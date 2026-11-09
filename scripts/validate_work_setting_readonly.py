"""Validate actual jobs_detail SQL using dbt SQL input mocks; SELECT/dry-run only.

Run dbt compile --select jobs_detail --no-introspect first. Uses ADC, never .env.
This bypasses dbt test's adapter temporary-table materialization. Expected rows
come from the native dbt unit-test YAML, not a separate classifier definition.
"""
import argparse
import datetime
import json
import re
from pathlib import Path

import yaml
from google.cloud import bigquery
from jinja2 import Environment


MAXIMUM_BYTES = 2_000_000_000


def checked_select(client, sql, *, parameters=(), execute=True):
    """No query executes unless BigQuery has first identified it as one SELECT."""
    options = dict(maximum_bytes_billed=MAXIMUM_BYTES, query_parameters=list(parameters))
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, **options))
    if dry.statement_type != 'SELECT':
        raise ValueError(f'Refusing non-SELECT statement: {dry.statement_type}')
    if (dry.total_bytes_processed or 0) > MAXIMUM_BYTES:
        raise ValueError('SELECT exceeds validation scan budget')
    job = client.query(sql, job_config=bigquery.QueryJobConfig(**options)) if execute else None
    return dry, job


def schema_types(schema):
    def dtype(field):
        aliases = {'INTEGER': 'int64', 'FLOAT': 'float64', 'BOOLEAN': 'boolean'}
        kind = aliases.get(field.field_type, field.field_type.lower())
        if field.field_type == 'RECORD':
            kind = 'struct<' + ','.join(f.name + ' ' + dtype(f) for f in field.fields) + '>'
        if field.mode == 'REPEATED':
            kind = 'array<' + kind + '>'
        return re.sub(r'\s+', '', kind)
    return {field.name: dtype(field) for field in schema}


def metadata_object(value):
    # BigQuery client versions may decode native JSON or return its JSON text.
    value = json.loads(value) if isinstance(value, str) else value
    if not isinstance(value, dict):
        raise ValueError('work_setting_metadata must be a JSON object')
    return value


def validate(client, sql, expected, label):
    dry, job = checked_select(client, sql)
    rows = [dict(row) for row in job.result()]
    assert schema_types(dry.schema)['work_setting'] == 'string'
    assert schema_types(dry.schema)['work_setting_metadata'] == 'json', 'metadata is not native JSON'
    for row in rows:
        row['work_setting_metadata'] = metadata_object(row['work_setting_metadata'])
    actual = {row['job_id']: row for row in rows}
    failures = []
    if len(actual) != len(rows) or set(actual) != {e['job_id'] for e in expected}:
        failures.append('row-grain / input-output ID mismatch')
    for e in expected:
        for key, value in e.items():
            if actual.get(e['job_id'], {}).get(key) != value:
                failures.append(f"{e['job_id']}.{key}: expected {value!r}, got {actual.get(e['job_id'], {}).get(key)!r}")
    for row in rows:
        if row['work_setting'] not in ('Office', 'Hybrid', 'Remote', 'Unknown'):
            failures.append(f"invalid setting: {row['job_id']}")
        metadata = row['work_setting_metadata']
        if set(metadata) != {'rule', 'evidence', 'confidence', 'conflict'}:
            failures.append(f"metadata keys invariant: {row['job_id']}")
        if not isinstance(metadata['conflict'], bool) or not isinstance(metadata['evidence'], list):
            failures.append(f"metadata native types invariant: {row['job_id']}")
        if metadata['conflict'] and row['work_setting'] != 'Unknown':
            failures.append(f"conflict invariant: {row['job_id']}")
        if row['work_setting'] == 'Unknown' and metadata['confidence'] != 'low':
            failures.append(f"confidence invariant: {row['job_id']}")
        if any(k.startswith('_ws_') for k in row) or any(k in row for k in (
            'work_setting_extensions', 'work_setting_highlights', 'work_from_home', 'work_setting_source_metadata',
            'work_setting_rule', 'work_setting_evidence', 'work_setting_confidence', 'work_setting_conflict'
        )):
            failures.append('private helper column leaked')
    print(json.dumps({'label': label, 'rows': len(rows), 'bytes': dry.total_bytes_processed,
                      'job_id': job.job_id, 'failures': failures}, indent=2))
    if failures:
        raise SystemExit(1)
    return rows, dry.schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='projects-portfolio-446806')
    parser.add_argument('--sample', type=Path, help='Optional independent snippet JSON; snippets are NOT complete postings')
    parser.add_argument('--graph-dry-run', action='store_true', help='Dry-run nonincremental/incremental SELECT graphs from deployed staging, no materialization')
    parser.add_argument('--previous-audit-snapshot', type=Path, help='Compare every label and complete audit object to pre-JSON-migration fixture results')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'dbt/target/manifest.json').read_text())
    node = manifest['nodes']['model.jobs_data_platform.jobs_detail']
    model = (root / 'dbt/target/compiled/jobs_data_platform/models/analysis/jobs_detail.sql').read_text()
    assert node['raw_code'].strip() == (root / 'dbt/models/analysis/jobs_detail.sql').read_text().strip(), 'stale dbt compile: model changed'
    assert node.get('compiled_code', '').strip() == model.strip(), 'compiled SQL differs from manifest; rerun dbt compile'
    for name in ('normalize_work_setting_text', 'work_setting_patterns'):
        macro = manifest['macros'][f'macro.jobs_data_platform.{name}']
        assert macro['macro_sql'].strip() == (root / f'dbt/macros/{name}.sql').read_text().strip(), f'stale {name} macro: rerun dbt compile'
    unit = yaml.safe_load((root / 'dbt/models/analysis/work_setting_unit_tests.yml').read_text())['unit_tests'][0]
    fixture = (root / 'dbt/tests/fixtures/work_setting_jobs.sql').read_text()

    def hydrate(input_sql):
        sql = model
        for mock in unit['given']:
            name = mock['input'].split("'")[1]
            relation = manifest['nodes'][f'model.jobs_data_platform.{name}']['relation_name']
            replacement = input_sql if name == 'dim_job_listings' else mock['rows']
            sql = sql.replace(relation, '(' + replacement + ')')
        return sql

    client = bigquery.Client(project=args.project)
    fixture_sql = hydrate(fixture)
    fixture_rows, fixture_schema = validate(client, fixture_sql, unit['expect']['rows'], 'native dbt unit fixtures')
    if args.previous_audit_snapshot:
        expected_audit = json.loads(args.previous_audit_snapshot.read_text())
        actual_audit = {r['job_id']: {'work_setting': r['work_setting'], 'metadata': r['work_setting_metadata']}
                        for r in fixture_rows}
        # Canonical JSON equality also distinguishes booleans from numeric 0/1;
        # Python's ordinary dict equality alone would not enforce that distinction.
        differences = [job_id for job_id in set(expected_audit) | set(actual_audit)
                       if json.dumps(expected_audit.get(job_id), sort_keys=True)
                       != json.dumps(actual_audit.get(job_id), sort_keys=True)]
        assert not differences, f'Label/audit migration regression: {sorted(differences)}'
        print(f'Exact pre/post audit snapshot: PASS ({len(actual_audit)} labels + complete rule/evidence/confidence/conflict)')
    baseline = fixture_sql.split(', work_setting_inputs as (')[0] + 'select * from add_dims'
    _, baseline_job = checked_select(client, baseline)
    baseline_rows = {r.job_id: dict(r) for r in baseline_job.result()}
    for row in fixture_rows:
        assert all(value == baseline_rows[row['job_id']][key] for key, value in row.items()
                   if not key.startswith('work_setting')), 'existing output column changed'
    print('Existing-column fixture regression: PASS')
    invariant = (root / 'dbt/tests/assert_jobs_detail_work_setting_invariants.sql').read_text()
    invariant = invariant.replace("{{ ref('jobs_detail') }}", '(' + fixture_sql + ')')
    _, invariant_job = checked_select(client, invariant)
    assert not list(invariant_job.result()), 'output invariant SQL failed'
    print('Actual singular invariant test on fixtures: PASS')

    if args.graph_dry_run:
        graph_dry_run(client, root, manifest, model, fixture_schema)
    if args.sample:
        # Substitute only fixture input JSON. Classifier and typed projection stay unchanged.
        sample = json.loads(args.sample.read_text())
        cases = [{'id': str(e['sample_number']), 'title': e['title'],
                  'description': '. '.join(e['evidence']),
                  'wfh': (e.get('metadata') or {}).get('work_from_home')}
                 for e in sample['examples']]
        start = fixture.index("json '''[")
        end = fixture.index("]'''", start) + 4
        # Sample text is untrusted DATA, never interpolated into executable SQL.
        sample_fixture = fixture[:start] + 'parse_json(@sample_json)' + fixture[end:]
        sql = hydrate(sample_fixture)
        _, job = checked_select(client, sql, parameters=[bigquery.ScalarQueryParameter('sample_json', 'STRING', json.dumps(cases))])
        rows = {r.job_id: dict(r) for r in job.result()}
        differences = [{'sample': e['sample_number'], 'source': e['source'], 'expected': e['expected'],
                        'actual': rows[str(e['sample_number'])]['work_setting']}
                       for e in sample['examples'] if rows[str(e['sample_number'])]['work_setting'] != e['expected']]
        print(json.dumps({'label': 'independent snippets (qualitative, not accuracy)', 'rows': len(rows),
                          'job_id': job.job_id, 'differences': differences}, indent=2))


def graph_dry_run(client, root, manifest, model, fixture_schema):
    """Hydrate ONLY new int/dimension SQL; deployed staging/day are read inputs.

    Production has no prep columns yet. Both branches render original int files
    with original prep macros. Partition dates are a local three-day test window;
    the production generate_partitions_to_replace macro remains untouched.
    """
    refs = {
        'stg_jobs_scraping__serpapi_jobs': '`projects-portfolio-446806.staging.stg_jobs_scraping__serpapi_jobs`',
        'stg_jobs_scraping__linkedin_scraped_jobs': '`projects-portfolio-446806.staging.stg_jobs_scraping__linkedin_scraped_jobs`',
        'stg_seeds__serpapi_query_versions': '`projects-portfolio-446806.staging.stg_seeds__serpapi_query_versions`',
        'int_jobs_scraping__serpapi_jobs': '_qa_serpapi',
        'int_jobs_scraping__linkedin_jobs': '_qa_linkedin',
        'dim_job_listings': '_qa_dim',
        'jobs_detail_day': '`projects-portfolio-446806.analysis.jobs_detail_day`',
    }
    dates = ["date('" + (datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=i)).isoformat() + "')" for i in range(3)]
    for incremental in (False, True):
        env = Environment(extensions=['jinja2.ext.do'])
        env.globals.update(config=lambda **kwargs: '', ref=lambda name: refs[name],
                           is_incremental=lambda: incremental, generate_partitions_to_replace=lambda: dates)
        for filename in ('normalize_work_setting_text.sql', 'serpapi_work_setting_inputs.sql'):
            module = env.from_string((root / 'dbt/macros' / filename).read_text()).make_module()
            env.globals.update({name: getattr(module, name) for name in dir(module) if not name.startswith('_')})
        int_sql = [env.from_string((root / f'dbt/models/int/int_jobs_scraping__{name}_jobs.sql').read_text()).render()
                   for name in ('serpapi', 'linkedin')]
        dim = (root / 'dbt/target/compiled/jobs_data_platform/models/marts/dim_job_listings.sql').read_text()
        assert manifest['nodes']['model.jobs_data_platform.dim_job_listings']['raw_code'].strip() == (root / 'dbt/models/marts/dim_job_listings.sql').read_text().strip(), 'stale dimension compile'
        assert manifest['nodes']['model.jobs_data_platform.dim_job_listings'].get('compiled_code', '').strip() == dim.strip(), 'dimension compiled SQL differs from manifest'
        detail = model
        for name, replacement in refs.items():
            relation = manifest['nodes'][f'model.jobs_data_platform.{name}']['relation_name']
            dim = dim.replace(relation, replacement)
            detail = detail.replace(relation, replacement)
        prefix = ('with _qa_serpapi as (' + int_sql[0] + '), _qa_linkedin as (' + int_sql[1]
                  + '), _qa_dim as (' + dim + ') ')
        sql = prefix + 'select * from (' + detail + ')'
        job, _ = checked_select(client, sql, execute=False)
        fields = {field.name for field in job.schema}
        assert not any(name.startswith('_ws_') for name in fields)
        assert {f for f in fields if f.startswith('work_setting')} == {'work_setting', 'work_setting_metadata'}
        assert schema_types(job.schema)['work_setting'] == 'string'
        assert schema_types(job.schema)['work_setting_metadata'] == 'json'
        assert schema_types(job.schema) == schema_types(fixture_schema), 'analysis graph exact type mismatch against actual-model fixture schema'
        contract = yaml.safe_load((root / 'dbt/models/marts/schema.yml').read_text())['models'][0]['columns']
        dim_sql = prefix + 'select * from _qa_dim'
        dim_job, _ = checked_select(client, dim_sql, execute=False)
        expected_types = {c['name']: re.sub(r'\s+', '', c['data_type'].lower()) for c in contract}
        assert expected_types == schema_types(dim_job.schema), f'dimension exact type contract mismatch: {schema_types(dim_job.schema)}'
        print(json.dumps({'label': 'hydrated production SELECT graph dry-run', 'incremental': incremental,
                          'bytes': job.total_bytes_processed, 'columns': len(fields),
                          'dimension_columns': len(dim_job.schema), 'job_id': job.job_id}))


if __name__ == '__main__':
    main()

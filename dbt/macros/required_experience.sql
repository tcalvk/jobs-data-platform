{# Pure JS shared with offline fixtures. Temporary UDF: no external service or
   persistent routine. sql_header is supported by BigQuery table materialization. #}
{% macro required_experience_js() %}
function parseExperience(inputs) {
  var evidence = [], values = [], degreePaths = [], ambiguityBounds = [], ambiguous = false;
  var optional = /\b(preferred|preferably|preferences?|desired|desirable|nice[- ]to[- ]have|a plus|bonus|ideally|optional|optionally)\b/;
  var required = /\b(required|requirements|minimum|must|essential|basic qualifications|what you bring|qualifications)\b/;
  var degree = /\b(bachelor'?s?|baccalaureate|master'?s?|associate'?s?|doctor|doctorate|doctoral|phd|ph\.d|bs|ms|ba|ma|degree)\b/;
  function norm(s) {
    return (s || '').toLowerCase().replace(/[\u2010-\u2015\u2212]/g, '-')
      .replace(/[\u2018\u2019]/g, "'").replace(/<br\s*\/?\s*>|<\/p>|<\/li>/gi, '\n')
      .replace(/<[^>]*>/g, ' ').replace(/&nbsp;|&#160;|\u00a0/g, ' ')
      .replace(/\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](one|two|three|four|five|six|seven|eight|nine))?\b/g,
        function(_, tens, units) {
          return String(({twenty:20,thirty:30,forty:40,fifty:50,sixty:60,seventy:70,eighty:80,ninety:90})[tens]
            + (units ? ['one','two','three','four','five','six','seven','eight','nine'].indexOf(units) + 1 : 0));
        })
      .replace(/\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)\b/g,
        function(w, number) { return String(['one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'].indexOf(number) + 1); })
      .replace(/(\d+)\s*\((\d+)\)/g, function(_, a, b) {
        // Keep conflicts local to their numeric evidence. Optional text must
        // never make a separate required clause ambiguous during normalization.
        return a + (a !== b ? '__number_conflict__' : '');
      }).replace(/\s+/g, ' ')
      // A between-range has one shared unit after both bounds. Reuse the
      // existing lower-bound range grammar without treating a conjunction
      // between independent unit-bearing skill requirements as a range.
      .replace(/\bbetween\s+(\d+(?:\.\d+)?(?:__number_conflict__)?)\s+and\s+(\d+(?:\.\d+)?(?:__number_conflict__)?)\s*(years?|yrs?|months?|mos?)\b/g, '$1-$2 $3');
  }
  function constraints(text) {
    // Independent clauses form AND constraints. Preserve an explicit OR edge
    // across punctuation/newlines, rather than allowing an OR anywhere in the
    // paragraph to swallow unrelated prefix/suffix requirements into a path.
    // Commas inside degree phrases and experience lists stay inside their clause.
    text = text.replace(/(?:,|\band\b|\bbut\b)\s*(?=(?:preferably|ideally|optionally|preferred|desired|optional)\b)/g, '\n')
      .replace(/(?:[,;]\s*|\b(?:and|but)\s+)?\b(?:additionally|also|furthermore|in addition|all applicants|all candidates|in all cases|regardless of degree)\b/g, '\n')
      // An already complete experience requirement followed by a new degree
      // clause is global, not part of that degree's alternative path.
      .replace(/,\s*(?=(?:a |an |have |hold |possess )?(?:bachelor|master|associate|doctor|bs\b|ms\b|ba\b|ma\b))/g, function(separator, index) {
        var prefix = text.slice(0, index).split(/[;\n]/).pop();
        return /\d[^;]*\bexperience\b/.test(prefix) ? '\n' : separator;
      });
    var result = [];
    text.split(/\n|[;\u2022]|[.!?](?=\s+[a-z0-9]|$)/).forEach(function(part) {
      part = part.trim().replace(/^[\u2022*-]\s*/, '');
      if (!part) return;
      var previous = result[result.length - 1];
      var option = /^option\s+\d+\s*:/.test(part);
      if (option) part = part.replace(/^option\s+\d+\s*:/, '__option_path__ ');
      var degreeLead = /^(?:bachelor|master|associate|doctorate|doctoral|phd)\b/;
      var adjacentDegreePaths = previous && degreeLead.test(previous) && degreeLead.test(part)
        && /\d/.test(previous) && /\d/.test(part) && /experience/.test(previous + part)
        && !optional.test(previous + part)
        && previous.match(degreeLead)[0] !== part.match(degreeLead)[0];
      if (previous && (option && previous.indexOf('__option_path__') >= 0 || adjacentDegreePaths)) {
        result[result.length - 1] += ' or ' + part;
      } else if (previous && (/^(?:or|alternatively)\b/.test(part) || /\bor\s*$/.test(previous))) {
        result[result.length - 1] += ' ' + part.replace(/^alternatively\b/, 'or');
      } else result.push(part);
    });
    return result;
  }
  function qualificationPaths(line) {
    // OR between disciplines/skills ('science or mathematics', 'practical or
    // collegiate experience') is not OR between applicant qualification paths.
    var parts = [], start = 0, re = /\bor\b/g, m;
    while ((m = re.exec(line)) !== null) {
      var right = line.slice(re.lastIndex).replace(/^[\s,;(]+/, '');
      var path = /^(?:(?:have|hold|possess)\s+)?(?:(?:a|an)\s+)?(?:bachelor'?s?|baccalaureate|master'?s?|associate'?s?|advanced degree|graduate degree|postgraduate degree|undergraduate degree|doctorate|doctoral|phd|bs\b|ms\b|ba\b|ma\b|__option_path__|(?:at least\s+)?\d+(?:\.\d+)?|graduation|proof of completion|completion of|equivalent combination|combination of education)\b/.test(right)
        || /^(?:(?:current|active|valid)\s+)[^.;]{0,100}\b(?:certification|license)\b/.test(right)
        || /^(?:[a-z]+\s+){0,4}(?:certification|license)\b/.test(right);
      if (path) { parts.push(line.slice(start, m.index)); start = re.lastIndex; }
    }
    parts.push(line.slice(start));
    return parts;
  }
  var prepared = [];
  (inputs || []).forEach(function(input) {
    var previous = prepared[prepared.length - 1];
    if (previous && previous.source === input.source && (/^\s*[\u2022*-]?\s*(?:or\b|alternatively\b)/i.test(input.text || '') || /\bor\s*$/i.test(previous.text || ''))) {
      previous.text = (previous.text || '') + ' ' + input.text;
    } else prepared.push({source: input.source, heading: input.heading, text: input.text});
  });
  prepared.forEach(function(input) {
    var heading = norm(input.heading);
    var nonRequirement = /\b(benefits|compensation|base pay range|salary ranges?|about us|about the company|our company)\b/;
    var scope = optional.test(heading) ? 'optional' : nonRequirement.test(heading) ? 'non_requirement' : 'unspecified';
    var experienceSection = /^(?:(?:required|minimum|professional|work|relevant)\s+)?experience\s*:?$/.test(heading);
    // Normalize per line so newlines remain heading boundaries.
    var text = (input.text || '').replace(/[\u200b-\u200f\u202a-\u202e\ufeff]/g, '')
      .replace(/\r\n?/g, '\n')
      // Flattened HTML often preserves capitalization but loses separators.
      // Restore those boundaries before lowercasing (experienceExperience,
      // QualificationsBachelor, USMinimum); never infer a year from seniority.
      .replace(/([a-z])([A-Z][a-z])/g, '$1\n$2').replace(/([A-Z]{2,})([A-Z][a-z])/g, '$1\n$2')
      .replace(/<br\s*\/?\s*>|<\/p>|<\/li>|<\/h[1-6]>/gi, '\n')
      .split('\n').map(norm).join('\n').replace(/\b([bm])\.([sa])\./g, '$1$2')
      .replace(/\bph\.?d\./g, 'phd')
      .replace(/(\d+(?:\.\d+)?)\s+or (?:more|greater)\s+(?=(?:years?|yrs?|months?|mos?)\b)/g, '$1+ ')
      .replace(/\.(?=[a-z])/g, '.\n').replace(/([a-z)])\.(?=\d)/g, '$1.\n')
      .replace(/([a-z])(?=\d+(?:\.\d+)?\s*\+?\s*(?:(?:-|to)\s*\d+(?:\.\d+)?\s*\+?)?\s*(?:years?|months?)\b)/g, '$1\n')
      .replace(/\b((?:preferred|minimum|basic|required|desired) (?:qualifications|requirements)|education and experience|what you have)\b\s*[:.]*\s*/g, '\n$1:\n')
      .replace(/\b(base pay range|salary ranges?)\s*:?\s*/g, '\n$1:\n')
      // An education preference followed by a new duration is a completed
      // education qualification, not a preferred-experience heading. Keep actual
      // Preferred Qualifications scope intact; only split the local claim.
      .replace(/\b(preferred|desired|a plus|nice[- ]to[- ]have)\s*(?=\d+(?:[- ]\d+)?\s*\+?\s*(?:years?|months?)\b)/g, function(marker, word, offset, all) {
        var prefix = all.slice(0, offset).split(/[\n.;]/).pop();
        return degree.test(prefix) && !/\d[^;]*\b(?:years?|months?)\b/.test(prefix) ? marker + '\n' : marker;
      })
      .replace(/\([^)]*\b(?:preferred|a plus|nice[- ]to[- ]have|not required)\b[^)]*\)\s*(?=\d+\s*\+?\s*(?:years?|months?)\b)/g, '$&\n')
      .replace(/\b(required|preferred)\s+(?=(?:national |professional |board )?(?:certification|license|degree|bachelor|master)\b)/g, '$1\n')
      .replace(/(?:^|\n)\s*[\u2022*-]\s*/g, '\n');
    constraints(text).forEach(function(line) {
      line = line.trim();
      if (!line) return;
      var colon = line.indexOf(':');
      var label = colon >= 0 ? line.slice(0, colon) : line;
      if (colon >= 0 && label.length < 60 && !/\d/.test(label)) {
        experienceSection = /^(?:(?:required|minimum|professional|work|relevant)\s+)?experience$/.test(label.trim());
      }
      if (label.length < 50 && !/\d/.test(label) && nonRequirement.test(label)) {
        scope = 'non_requirement';
        if (colon < 0 || colon === line.length - 1) return;
      }
      var sectionHeading = /^(?:(?:preferred|desired|minimum|basic|required|essential)(?:\s+(?:qualifications|(?:hiring )?requirements|skills(?: and experience)?|experience))?|qualifications|requirements|what you bring|nice[- ]to[- ]have)\s*$/.test(label.trim());
      if (sectionHeading && !/\d/.test(label) && (optional.test(label) || required.test(label))) {
        scope = optional.test(label) ? 'optional' : 'required';
        if (colon < 0 || colon === line.length - 1) return;
      }
      var hits = [], match, branches = qualificationPaths(line);
      var degreeContext = branches.length > 1 && branches.every(function(branch) { return degree.test(branch) || branch.indexOf('__option_path__') >= 0; });
      var re = /\b(\d+(?:\.\d+)?)(?:__number_conflict__)?\s*(?:\+|(?:-|to)\s*\d+(?:\.\d+)?\s*\+?)?\s*[- ]?\s*(years?|yrs?|months?|mos?)\b/g;
      while ((match = re.exec(line)) !== null) {
        var before = line.slice(Math.max(0, match.index - 70), match.index);
        var after = line.slice(re.lastIndex, re.lastIndex + 110);
        // One mixed-unit duration is additive, unlike separate skill thresholds.
        // Consume only the month token here so its optional/required suffix still
        // participates in the scope check below.
        var compound = /^y/.test(match[2]) && /^\s*(?:,\s*)?(?:and\s+)?(\d+(?:\.\d+)?)\s*(months?|mos?)\b(?=\s*(?:of\s+)?(?:[a-z/+&-]+\s+){0,12}experience\b)/.exec(after);
        var durationEnd = re.lastIndex + (compound ? compound[0].length : 0);
        // Require duration adjacent to applicant experience, not company age,
        // education duration, paid leave, contract length, or certification timing.
        var experience = /^\s*'?\s*(?:of\s+)?(?:[a-z][a-z/+&-]*\s+){0,12}experience\b/.test(after)
          || /\bexperience\s*(?:of|:|>=|at least|minimum)?\s*$/.test(before)
          || /^\s+in\s+(?:an?\s+)?(?:[a-z/-]+\s+){0,5}(?:role|position)\b/.test(after)
          || degreeContext
          || input.source === 'title'
          || (/^\s*(?:is |are )?(?:required|preferred|desired)\b/.test(after)
              && !/\b(contract|commitment|tenure|service|warranty|certification|license|degree|education)\b/.test(line))
          || (degree.test(before) && /^\s*[,;]?\s*or\b/.test(after) && /\bexperience\b/.test(line));
        var workDuration = /^\s*(?:of\s+)?(?:in\s+|developing\b|deploying\b|provisioning\b|building\b|managing\b|leading\b|supporting\b|designing\b)/.test(after);
        var applicant = /\b(?:candidates?|applicants?|you)\s+(?:(?:should|must|will|need to)\s+)?have\b/.test(before);
        experience = experience || (workDuration && (experienceSection || scope === 'required' || applicant));
        // Bind an entire comma/AND list to its shared trailing experience noun.
        // Skills between duration tokens distinguish a list from one compound
        // duration. Never bridge OR, preference language or non-work durations.
        var noun = after.search(/\bexperience\b/);
        var sharedPrefix = noun < 0 ? '' : after.slice(0, noun);
        var shared = noun >= 0 && /^\s*(?:of\s+)?[a-z /+&-]*(?:,\s*(?:and\s+)?|\band\b|&)\s*\d/.test(sharedPrefix)
          && !/\bor\b|\b(contract|service|age|degree|tenure|warranty|vacation|vesting)\b/.test(sharedPrefix)
          && !optional.test(sharedPrefix);
        experience = experience || shared || !!compound;
        if (!experience) continue;
        if (input.source === 'title' && /^\s*[- ]?(?:degree|contract|commitment|warranty|anniversary)\b/.test(after)) continue;
        var next = line.slice(durationEnd).search(/\b\d+(?:\.\d+)?\s*(?:\+|[-])?\s*(?:years?|months?|yrs?|mos?)\b/);
        var tail = line.slice(durationEnd, next < 0 ? line.length : durationEnd + next);
        var localBefore = before.slice(Math.max(before.lastIndexOf(','), before.lastIndexOf(';'), before.lastIndexOf(' but ')) + 1);
        // A parenthetical preference for a skill is not a preference for the
        // preceding numeric minimum. A numeric duration inside that parenthesis
        // still sees its own trailing optional marker and remains excluded.
        var scopeTail = tail.replace(/\([^)]*\b(?:preferred|desired|desirable|optional)\b[^)]*\)/g, '');
        var localOptional = optional.test(scopeTail) || optional.test(localBefore)
          || /\bnot\s+(?:required|necessary|needed)\b/.test(tail);
        var explicitRequired = /\b(required|must|minimum|at least)\b/.test(before + tail);
        var employer = /\b(?:we (?:are|have)|we've|our (?:company|team|engineers)|group\/division|(?:company|organization|division|firm|business|producer|provider)\b[^.;]{0,80}\b(?:with|has|have|brings?|over))/.test(before)
          || /\b(?:backed by|brings? (?:the )?(?:strength|expertise|legacy|heritage)|history of|legacy of)\b/.test(before)
          || /\b(?:we (?:are|have)|we've|we're|chipmakers|will support you|support you as you develop)\b/.test(line)
          || /\bengineers with experience levels\b/.test(before);
        var nonApplicant = employer || /^\s*(?:of\s+)?age\b/.test(after)
          || /\b(?:sign[- ]on|bonus|incentive|vesting|paid leave|vacation)\b/.test(tail)
          || /\b(?:sign[- ]on|bonus|incentive|vesting)\b/.test(localBefore)
          || /\bcombination of (?:work history|work experience|experience)[^.;]{0,40}\beducation\b/.test(tail)
          || (/\b(?:candidates|applicants|those|individuals) with\b/.test(before) && /\b(?:must|will|should) (?:obtain|complete|receive|earn)\b/.test(tail));
        if (nonApplicant) {
          evidence.push({source: input.source, text: line, years: null, status: 'ignored_non_applicant'});
          continue;
        }
        if (/\b(?:substituted for|substitution|in lieu of)\b/.test(line)
            || /\bin (?:other|certain|specific|select) locations\b|\bfor [a-z ,&-]{1,60} locations\b/.test(tail)) {
          ambiguous = true;
          evidence.push({source: input.source, text: line, years: null, status: 'ambiguous_conditional_requirement'});
          continue;
        }
        if (scope === 'non_requirement' && !explicitRequired) continue;
        if (localOptional || scope === 'optional') {
          evidence.push({source: input.source, text: line, years: null, status: 'ignored_optional'});
          continue;
        }
        if (match[0].indexOf('__number_conflict__') >= 0) {
          ambiguous = true;
          evidence.push({source: input.source, text: line, years: null, status: 'ambiguous_numeric_conflict'});
          continue;
        }
        if (/\b(company|our team|our engineers|we have|we bring|combined|collective|founded|established|benefits|vacation|paid leave|warranty|employment history|past|years of service)\b/.test(before) && !explicitRequired) continue;
        var n = Number(match[1]);
        var years = /^mo/.test(match[2]) ? (n < 12 ? 0 : Math.ceil(n / 12)) : Math.ceil(n);
        if (compound) years = Math.ceil(n + Number(compound[1]) / 12);
        if (!Number.isSafeInteger(years) || /\b(up to|less than|under|at most|maximum)\s*$/.test(before)) {
          ambiguous = true;
          evidence.push({source: input.source, text: line, years: null, status: 'ambiguous_numeric_bound'});
          continue;
        }
        if (compound) re.lastIndex = durationEnd;
        hits.push({years: years, index: match.index});
      }
      var noExperience = /\bno\s+(?:(?:prior|previous|professional|work|relevant|related)\s+){0,3}experience\s+(?:is\s+)?(?:required|necessary|needed)\b/.test(line)
        || /\b(?:work |professional |prior )?experience\s*:\s*none\b/.test(line)
        || (experienceSection && /^none\b/.test(line))
        || (!/\d/.test(line) && /\bexperience\s+(?:is\s+)?not\s+(?:required|necessary|needed)\b/.test(line));
      if (noExperience && scope !== 'optional') hits.push({years: 0, index: 0});
      if (!hits.length) return;
      // A comma after a complete experience clause inside a degree alternative
      // can introduce either a branch-local threshold or a global requirement.
      // Without an explicit AND/global boundary, that scope is not recoverable.
      if (branches.length > 1 && branches.some(function(branch) { return /\bexperience\b[^,;]*,\s*(?:and\s+)?\d/.test(branch); })) {
        ambiguous = true;
        evidence.push({source: input.source, text: line, years: null, status: 'ambiguous_constraint_scope'});
        return;
      }
      var pathOffset = 0;
      var pathHits = branches.map(function(branch) {
        var found = hits.filter(function(hit) { return hit.index >= pathOffset && hit.index < pathOffset + branch.length; });
        pathOffset += branch.length + 2;
        return found;
      });
      if (branches.length > 1 && (/equivalent (?:combination|experience)|combination of education/.test(line)
          || pathHits.some(function(found) { return !found.length; }))) {
        // A fully quantified alternative supplies an upper bound on the minimum
        // across paths. A separate larger mandatory threshold can dominate this
        // uncertainty without pretending the unquantified path requires zero.
        ambiguityBounds.push(Math.max.apply(null, hits.map(function(h) { return h.years; })));
        evidence.push({source: input.source, text: line, years: null, status: 'unquantified_alternative'});
        return;
      }
      var alternative = branches.length > 1 && hits.length > 1
        && branches.some(function(branch) { return degree.test(branch) || branch.indexOf('__option_path__') >= 0; })
        && pathHits.every(function(found) { return found.length > 0; });
      if (branches.length > 1 && hits.length > 1 && !alternative) {
        ambiguous = true;
        evidence.push({source: input.source, text: line, years: null, status: 'ambiguous_alternatives'});
        return;
      }
      var nums = hits.map(function(h) { return h.years; });
      var value;
      if (alternative) {
        branches.forEach(function(branch) { degreePaths.push(branch.replace(/^[\s,;]+|[\s,;]+$/g, '')); });
        var offset = 0;
        var paths = branches.map(function(branch) {
          var inBranch = hits.filter(function(h) { return h.index >= offset && h.index < offset + branch.length; });
          offset += branch.length + 2; // the literal 'or' removed by split
          if (!inBranch.length) { ambiguous = true; return null; }
          return Math.max.apply(null, inBranch.map(function(h) { return h.years; }));
        });
        value = Math.min.apply(null, paths);
      } else value = Math.max.apply(null, nums);
      values.push(value);
      evidence.push({source: input.source, text: line, years: value, status: alternative ? 'minimum_degree_path' : 'required_numeric'});
    });
  });
  // SerpAPI often repeats a description's conditional degree branch as a
  // separate highlight. Do not accidentally turn that identical branch into an
  // unconditional extra requirement when combining sources.
  evidence.forEach(function(e) {
    if (e.status === 'required_numeric' && degreePaths.indexOf(e.text.replace(/^[\s,;]+|[\s,;]+$/g, '')) >= 0) e.status = 'covered_degree_path';
  });
  values = evidence.filter(function(e) { return e.status === 'required_numeric' || e.status === 'minimum_degree_path'; })
    .map(function(e) { return e.years; });
  if (ambiguityBounds.length && (!values.length || Math.max.apply(null, values) < Math.max.apply(null, ambiguityBounds))) ambiguous = true;
  if (values.indexOf(0) >= 0 && values.some(function(v) { return v > 0; }) && evidence.some(function(e) { return /no.*experience|experience.*not required/.test(e.text); })) ambiguous = true;
  return {years: ambiguous || !values.length ? null : Math.max.apply(null, values),
    status: ambiguous ? 'ambiguous' : values.length ? 'explicit_requirement' : 'unspecified', evidence: evidence};
}
return parseExperience(inputs);
{% endmacro %}

{% macro required_experience_udf() %}
create temp function parse_required_experience(inputs array<struct<source string, heading string, text string>>)
returns struct<years int64, status string, evidence array<struct<source string, text string, years int64, status string>>>
language js as r"""
{{ required_experience_js() }}
""";
{% endmacro %}

{% macro required_experience_inputs() %}
array_concat(
  [struct('title' as source, '' as heading, job_title as text),
   struct('description' as source, '' as heading, job_description as text),
   struct('linkedin_preferences' as source, '' as heading, work_setting_source_metadata as text)],
  array(select as struct concat('highlight:', coalesce(h.title, '')) as source,
        h.title as heading, h.item as text from unnest(work_setting_highlights) h),
  array(select as struct 'serpapi_extension' as source, '' as heading, e as text
        from unnest(work_setting_extensions) e)
)
{% endmacro %}

{# dbt 1.11's unit materialization creates its schema-probe table and its final
   SELECT in different query jobs. A TEMP FUNCTION from the first job does not
   survive into the second. Older versions do not propagate sql_header to that
   SELECT; scope this compatibility shim strictly to models using this parser.
   Newer versions which propagate the header need no duplicate declaration. #}
{% macro bigquery__get_unit_test_sql(main_sql, expected_fixture_sql, expected_column_names) %}
  {% if 'parse_required_experience(' in main_sql and not flags.REQUIRE_SQL_HEADER_IN_TEST_CONFIGS %}
    {{ required_experience_udf() }}
  {% endif %}
  {{ dbt.default__get_unit_test_sql(main_sql, expected_fixture_sql, expected_column_names) }}
{% endmacro %}

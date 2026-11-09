{% macro work_setting_patterns() %}
{# Version-one patterns are bounded within a sentence; no inference from
   missing WFH, generic company policy or geography. Resolution stays downstream. #}
{% set role_hybrid = '\\b(?:hybrid (?:role|position|schedule|arrangement)|(?:role|position|work arrangement|workplace|schedule)\\s*:? (?:is |will be |follows a )?hybrid)\\b' %}
{% set recurring = '\\b(?:alternat(?:e|ing) weeks?|[1-5] days? (?:per|a|each) week|every (?:week|monday|tuesday|wednesday|thursday|friday))\\b' %}
{% set role_office = '\\b(?:(?:role|position|job) (?:is |will be |requires? |must be )?(?:fully |100% )?(?:onsite|on-site|in[- ]office)|(?:work|working|based|be|required|report|reporting) (?:fully |100% )?(?:onsite|on-site|in[- ]office)|(?:onsite|on-site|in[- ]office) (?:role|position|opportunity|attendance))\\b' %}
{% set role_remote = '\\b(?:(?:role|position|job) (?:is |will be |can be )?(?:fully |100% |primarily |predominantly )?remote|remote (?:role|position|job)|(?:you will|you can|you may|eligible to|will) work (?:remotely|from home)|work (?:location|arrangement): ?remote)\\b|^(?:fully|100%) remote$' %}
{% set ambiguity = '\\b(?:(?:remote|hybrid|onsite|on-site)\\s*(?:/|or)\\s*(?:remote|hybrid|onsite|on-site)|(?:initially|temporarily|eventually|after training|subject to approval|depending on|may become|could become)[^.;]{0,65}(?:remote|hybrid|onsite|on-site)|(?:remote|hybrid|onsite|on-site)[^.;]{0,55}(?:subject to approval|depending on|after training))\\b' %}
{# Strip the complete local negated attendance phrase, in active OR passive
   voice. Never suppress another positive clause just because it shares a sentence. #}
{% set negation = '\\b(?:(?:not (?:eligible for |available for |a |an )?|no |cannot |can not |not permitted to |does not (?:allow|offer|support) )(?:fully |100% )?(?:remote(?: work)?|work (?:remotely|from home)|hybrid)(?: or hybrid)?|(?:remote(?: work| working)?|working (?:remotely|from home)|work from home|hybrid(?: work)?)(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:available|allowed|permitted|offered|supported)(?: for this role)?)\\b' %}
{# Lack of obligation is NEUTRAL, not a prohibition or affirmative cadence.
   Strip it before extracting day components as well as before positive signals. #}
{% set remote_neutral = '\\b(?:(?:not (?:required|necessary|mandatory|obliged|expected) to |(?:does|do|will) not (?:require|need|mandate) (?:(?:you|employees|candidates) to )?)(?:work (?:remotely|from home)|be remote)|(?:work(?:ing)? from home|work(?:ing)? remotely|remote(?: work)?|wfh)(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:required|necessary|mandatory))\\b' %}
{% set office_negation = '\\b(?:(?:not (?:an? )?|no |(?:does|do|will) not (?:require|need|mandate) (?:(?:(?:you|employees|candidates) to )?(?:work|be) |working )?|(?:is |are )?not (?:required|necessary|mandatory|obliged|expected) (?:to (?:work|be) )?)(?:onsite|on-site|in[- ]office)(?: (?:attendance|role|position|work))?|(?:work(?:ing)? |attendance )?(?:onsite|on-site|in[- ]office)(?: (?:attendance|work))?(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:required|mandatory|necessary|available))\\b' %}
{% set office_week = '\\bwork (?:onsite|on-site|in[- ]office) ([1-4]) days? (?:per|a|each) week\\b' %}
{% set remote_week = '\\bwork (?:remotely|from home) ([1-4]) days? (?:per|a|each) week\\b' %}
{{ return({
    'role_hybrid': role_hybrid,
    'recurring': recurring,
    'role_office': role_office,
    'role_remote': role_remote,
    'ambiguity': ambiguity,
    'negation': negation,
    'remote_neutral': remote_neutral,
    'office_negation': office_negation,
    'office_week': office_week,
    'remote_week': remote_week
}) }}
{% endmacro %}

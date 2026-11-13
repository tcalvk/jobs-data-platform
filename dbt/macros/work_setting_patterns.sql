{% macro work_setting_patterns() %}
{# Bounded explicit patterns. Resolution and opt-in low-confidence inference
   stay downstream; missing WFH and geography never establish Office. #}
{% set role_hybrid = '\\b(?:hybrid (?:role|position|schedule|arrangement)|(?:role|position|work arrangement|workplace|schedule)\\s*:? (?:is |will be |follows a |uses a |has a )?hybrid)\\b' %}
{% set recurring = '\\b(?:alternat(?:e|ing) weeks?|[1-5] days? (?:per|a|each) week|every (?:week|monday|tuesday|wednesday|thursday|friday)|fridays?)\\b' %}
{% set role_office = '\\b(?:(?:role|position|job) (?:is |will be |requires? |must be )?(?:fully |100% )?(?:onsite|on-site|in[- ]office|office-based|in-person)|(?:work|working|based|be|required|report|reporting|performed) (?:fully |100% )?(?:onsite|on-site|in[- ]office|in[- ]person)|(?:onsite|on-site|in[- ]office|office-based|in[- ]person) (?:role|position|opportunity|attendance)|work location: ?in person|(?:consistent|regular) in-person (?:presence|attendance|engagement))\\b' %}
{% set role_remote = '\\b(?:(?:role|position|job) (?:is |will be |can be )?(?:fully |100% |primarily |predominantly )?remote|(?:role|position) is based remotely|remote (?:role|position|job|opportunity)|(?:you will|you can|you may|eligible to|will) work (?:remotely|from home)|work (?:location|arrangement): ?remote)\\b|^(?:fully|100%) remote$' %}
{% set ambiguity = '\\b(?:(?:remote|hybrid|onsite|on-site|office-based|in[- ]person)(?:\\s*[,;(]+\\s*(?:(?:/|or)\\s*)?|\\s*(?:/|or)\\s*)(?:remote|hybrid|onsite|on-site|office-based|in[- ]person)|(?:initially|temporarily|eventually|after training|subject to approval|depending on|may become|could become)[^.;]{0,65}(?:remote|hybrid|onsite|on-site|office-based)|(?:remote|hybrid|onsite|on-site|office-based)[^.;]{0,55}(?:subject to approval|depending on|after training)|(?:work(?:ing)? )?(?:remotely|from home) (?:for )?[1-5] days? (?:per|a|each) (?:month|quarter|year)|(?:work(?:ing)? )?(?:onsite|on-site|in[- ]office) (?:for )?[1-5] days? (?:per|a|each) (?:month|quarter|year)|[1-5] days? (?:onsite|on-site|in[- ]office) (?:per|a|each)? ?(?:month|quarter|year|monthly|quarterly|yearly))\\b' %}
{# Strip the complete local negated attendance phrase, in active OR passive
   voice. Never suppress another positive clause just because it shares a sentence. #}
{% set negation = '\\b(?:(?:not (?:eligible for |available for |structured as a |structured as an |a |an )?|no |cannot |can not |not permitted to |does not (?:allow|offer|support) )(?:fully |100% )?(?:remote(?: work| position| role)?|work (?:remotely|from home)|hybrid)(?: or hybrid)?|(?:remote(?: work| working)?|working (?:remotely|from home)|work from home|hybrid(?: work)?)(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:available|allowed|permitted|offered|supported)(?: for this role)?)\\b' %}
{# Lack of obligation is NEUTRAL, not a prohibition or affirmative cadence.
   Strip it before extracting day components as well as before positive signals. #}
{% set remote_neutral = '\\b(?:(?:not (?:required|necessary|mandatory|obliged|expected) to |(?:does|do|will) not (?:require|need|mandate) (?:(?:you|employees|candidates) to )?)(?:work (?:remotely|from home)|be remote)|(?:work(?:ing)? from home|work(?:ing)? remotely|remote(?: work)?|wfh)(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:required|necessary|mandatory))\\b' %}
{% set office_negation = '\\b(?:(?:not (?:an? )?|no |(?:does|do|will) not (?:require|need|mandate) (?:(?:(?:you|employees|candidates) to )?(?:work|be) |working )?|(?:is |are )?not (?:required|necessary|mandatory|obliged|expected) (?:to (?:work|be) )?)(?:onsite|on-site|in[- ]office)(?: (?:attendance|role|position|work))?|(?:work(?:ing)? |attendance )?(?:onsite|on-site|in[- ]office)(?: (?:attendance|work))?(?: [1-5] days? (?:per|a|each) week)? (?:(?:is |will be )?not |will not be )(?:required|mandatory|necessary|available))\\b' %}
{% set office_week = '\\b(?:work(?:ing)? )?(?:onsite|on-site|in[- ]office)(?: in [a-z ]{1,35})? (?:for )?([1-4]) days?(?: (?:per|a|each) week| and [1-4] days? remotely)\\b' %}
{% set office_days_lead = '\\b([1-4]) days? (?:onsite|on-site|in[- ]office)\\b' %}
{% set remote_week = '\\bwork (?:remotely|from home) (?:for )?([1-4]) days? (?:per|a|each) week\\b' %}
{% set remote_tail = '\\b([1-4]) days? (?:remotely|remote)\\b' %}
{% set friday_home = '\\bwork from home (?:on )?fridays?\\b' %}
{# Interview/application/training logistics are not role attendance. #}
{% set office_logistics = '[^.;]*\\b(?:interviews?|interviewing|applications?|recruiting|recruitment|training|orientation|onboarding|conferences?|meetups?|team events?|company events?)\\b[^.;]*' %}
{# Substantive office wording survives logistics stripping; bare "be in person" does not. #}
{% set office_substantive = '\\b(?:(?:role|position|job) (?:is |will be |requires? |must be )?(?:fully |100% )?(?:onsite|on-site|in[- ]office|office-based|in-person)|(?:onsite|on-site|in[- ]office|office-based) (?:role|position|opportunity)|(?:work|working) (?:fully |100% )?(?:onsite|on-site|in[- ]office)|work location: ?in person|(?:consistent|regular) in-person (?:presence|attendance))\\b' %}
{% set office_label_negation = '\\b(?:not (?:an? )?|no )(?:office-based|in-person)(?: (?:role|position|attendance))?\\b' %}
{# Company-wide assertions only, never menus, perks or an offered option. #}
{% set company_remote = '\\b(?:we are|our company is|the company is) (?:a )?(?:fully|100%) remote (?:company|organization|business)\\b' %}
{% set company_hybrid = '\\b(?:we|our company|the company) (?:operate|operates|follow|follows|use|uses) (?:in |on |under )?(?:a )?hybrid (?:work |working )?model\\b' %}
{% set company_guard = '\\b(?:not|no|if|may|might|could|depending|options?|offer|offers|benefits?)\\b' %}
{# Physical DUTY verbs + concrete patient/procedure/equipment/custody objects.
   Titles, credentials and generic industry terms are deliberately insufficient. #}
{% set physical_care = '\\b(?:(?:prepare|prepares|preparing) patients for (?:examination|treatment)|(?:room|rooms|rooming) patients|(?:administer|administers|administering|give|gives|giving) (?:medications, )?(?:injections|immunizations|vaccines)|(?:perform|performs|performing|assist|assists|assisting) (?:with )?(?:phlebotomy|blood draws|physical examinations|physical exams)|(?:conduct|conducts|conducting) (?:physical assessment|forensic exam)|(?:lift|lifting|transfer|transferring) patients|(?:provide|provides|providing)[^.;]{0,60}(?:direct patient care|nursing care)[^.;]{0,100}(?:hospital|inpatient|bedside|clinic))\\b' %}
{% set physical_operations = '\\b(?:(?:pilot|pilots|piloting|fly|flies|flying|operate|operates|operating) (?:an? |the )?(?:helicopter|aircraft|airplane)|(?:provide|provides|providing) medical air transportation|(?:perform|performs|performing|conduct|conducts|conducting) (?:pre-flight|post-flight|aircraft) inspections|(?:operate|operates|operating|maintain|maintains|maintaining|repair|repairs|repairing) (?:an? |the )?(?:forklift|lathe|cnc machine|production machinery|physical machinery|heavy equipment)|(?:escort|escorts|escorting|search|searches|searching|supervise|supervises|supervising|restrain|restrains|restraining|transport|transports|transporting) (?:inmates|detainees|prisoners))\\b' %}
{% set physical_guard = '\\b(?:not|no|never|if|may|might|could|would|hypothetical|previous|prior|experience|knowledge|familiarity|training|trained|course|software|simulat[a-z]*|design|designing|designs|develop|developing|develops|virtual|telehealth|telemedicine|telephone|phone|video|online|remote|remotely|tele-?operated|tele-?operation)\\b|\\bour (?:company|clients?|customers?|teams?|organization|mission|hospitals?|hospital system|health system|clinics?|practices?|facilit(?:y|ies)|partners?|stores?|sites?)\\b|\\b(?:at|across|for|within) (?:our |the )?(?:partners?|clients?|hospitals?|clinics?|facilit(?:y|ies)|stores?|sites?)\\b|\\bteams? (?:that|who)\\b|\\bwe (?:provide|deliver)\\b' %}
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
    'office_days_lead': office_days_lead,
    'remote_week': remote_week,
    'remote_tail': remote_tail,
    'friday_home': friday_home,
    'office_logistics': office_logistics,
    'office_substantive': office_substantive,
    'office_label_negation': office_label_negation,
    'company_remote': company_remote,
    'company_hybrid': company_hybrid,
    'company_guard': company_guard,
    'physical_care': physical_care,
    'physical_operations': physical_operations,
    'physical_guard': physical_guard
}) }}
{% endmacro %}

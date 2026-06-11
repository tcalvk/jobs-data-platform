select *
from {{ ref('search_term_opportunity_score_month') }}
where (opportunity_score >= 80 and opportunity_tier != 'Strong Opportunity')
    or (opportunity_score >= 60 and opportunity_score < 80 and opportunity_tier != 'Good Opportunity')
    or (opportunity_score >= 40 and opportunity_score < 60 and opportunity_tier != 'Moderate Opportunity')
    or (opportunity_score < 40 and opportunity_tier != 'Weak Opportunity')
    or (opportunity_score is null and opportunity_tier != 'Insufficient Data')

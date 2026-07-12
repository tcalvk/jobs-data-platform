with jobs_detail as (
    select * from {{ ref('jobs_detail') }}
)

, skills as (
    select * from {{ ref('format_skills') }}
)

, search_term_opportunity_score_month as (
    select

        month_start_date,
        search_term,
        search_location,
        opportunity_score,
        opportunity_tier

    from {{ ref('search_term_opportunity_score_month') }}
)

, joined as (

    select
        jd.*,
        date_trunc(jd.posted_date, month) as month_start_date,
        st.opportunity_score,
        st.opportunity_tier,
        s.skill
    from jobs_detail jd 
    left join search_term_opportunity_score_month st
        on date_trunc(jd.posted_date, month) = st.month_start_date
        and jd.search_term = st.search_term
        and jd.search_location = st.search_location
    left join skills s
        on jd.job_id = s.job_id and jd.data_source = s.data_source
        
)

select * from joined
where skill is not null 

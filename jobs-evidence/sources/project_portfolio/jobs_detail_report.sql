with state_centers as (

    select * from unnest([
        struct('AL' as state_abbr, 'Alabama' as state_name, 32.8067 as lat, -86.7911 as long),
        struct('AK' as state_abbr, 'Alaska' as state_name, 61.3707 as lat, -152.4044 as long),
        struct('AZ' as state_abbr, 'Arizona' as state_name, 33.7298 as lat, -111.4312 as long),
        struct('AR' as state_abbr, 'Arkansas' as state_name, 34.9697 as lat, -92.3731 as long),
        struct('CA' as state_abbr, 'California' as state_name, 36.1162 as lat, -119.6816 as long),
        struct('CO' as state_abbr, 'Colorado' as state_name, 39.0598 as lat, -105.3111 as long),
        struct('CT' as state_abbr, 'Connecticut' as state_name, 41.5978 as lat, -72.7554 as long),
        struct('DE' as state_abbr, 'Delaware' as state_name, 39.3185 as lat, -75.5071 as long),
        struct('DC' as state_abbr, 'District of Columbia' as state_name, 38.8974 as lat, -77.0268 as long),
        struct('FL' as state_abbr, 'Florida' as state_name, 27.7663 as lat, -81.6868 as long),
        struct('GA' as state_abbr, 'Georgia' as state_name, 33.0406 as lat, -83.6431 as long),
        struct('HI' as state_abbr, 'Hawaii' as state_name, 21.0943 as lat, -157.4983 as long),
        struct('ID' as state_abbr, 'Idaho' as state_name, 44.2405 as lat, -114.4788 as long),
        struct('IL' as state_abbr, 'Illinois' as state_name, 40.3495 as lat, -88.9861 as long),
        struct('IN' as state_abbr, 'Indiana' as state_name, 39.8494 as lat, -86.2583 as long),
        struct('IA' as state_abbr, 'Iowa' as state_name, 42.0115 as lat, -93.2105 as long),
        struct('KS' as state_abbr, 'Kansas' as state_name, 38.5266 as lat, -96.7265 as long),
        struct('KY' as state_abbr, 'Kentucky' as state_name, 37.6681 as lat, -84.6701 as long),
        struct('LA' as state_abbr, 'Louisiana' as state_name, 31.1695 as lat, -91.8678 as long),
        struct('ME' as state_abbr, 'Maine' as state_name, 44.6939 as lat, -69.3819 as long),
        struct('MD' as state_abbr, 'Maryland' as state_name, 39.0639 as lat, -76.8021 as long),
        struct('MA' as state_abbr, 'Massachusetts' as state_name, 42.2302 as lat, -71.5301 as long),
        struct('MI' as state_abbr, 'Michigan' as state_name, 43.3266 as lat, -84.5361 as long),
        struct('MN' as state_abbr, 'Minnesota' as state_name, 45.6945 as lat, -93.9002 as long),
        struct('MS' as state_abbr, 'Mississippi' as state_name, 32.7416 as lat, -89.6787 as long),
        struct('MO' as state_abbr, 'Missouri' as state_name, 38.4561 as lat, -92.2884 as long),
        struct('MT' as state_abbr, 'Montana' as state_name, 46.9219 as lat, -110.4544 as long),
        struct('NE' as state_abbr, 'Nebraska' as state_name, 41.1254 as lat, -98.2681 as long),
        struct('NV' as state_abbr, 'Nevada' as state_name, 38.3135 as lat, -117.0554 as long),
        struct('NH' as state_abbr, 'New Hampshire' as state_name, 43.4525 as lat, -71.5639 as long),
        struct('NJ' as state_abbr, 'New Jersey' as state_name, 40.2989 as lat, -74.5210 as long),
        struct('NM' as state_abbr, 'New Mexico' as state_name, 34.8405 as lat, -106.2485 as long),
        struct('NY' as state_abbr, 'New York' as state_name, 42.1657 as lat, -74.9481 as long),
        struct('NC' as state_abbr, 'North Carolina' as state_name, 35.6301 as lat, -79.8064 as long),
        struct('ND' as state_abbr, 'North Dakota' as state_name, 47.5289 as lat, -99.7840 as long),
        struct('OH' as state_abbr, 'Ohio' as state_name, 40.3888 as lat, -82.7649 as long),
        struct('OK' as state_abbr, 'Oklahoma' as state_name, 35.5653 as lat, -96.9289 as long),
        struct('OR' as state_abbr, 'Oregon' as state_name, 44.5720 as lat, -122.0709 as long),
        struct('PA' as state_abbr, 'Pennsylvania' as state_name, 40.5908 as lat, -77.2098 as long),
        struct('RI' as state_abbr, 'Rhode Island' as state_name, 41.6809 as lat, -71.5118 as long),
        struct('SC' as state_abbr, 'South Carolina' as state_name, 33.8569 as lat, -80.9450 as long),
        struct('SD' as state_abbr, 'South Dakota' as state_name, 44.2998 as lat, -99.4388 as long),
        struct('TN' as state_abbr, 'Tennessee' as state_name, 35.7478 as lat, -86.6923 as long),
        struct('TX' as state_abbr, 'Texas' as state_name, 31.0545 as lat, -97.5635 as long),
        struct('UT' as state_abbr, 'Utah' as state_name, 40.1500 as lat, -111.8624 as long),
        struct('VT' as state_abbr, 'Vermont' as state_name, 44.0459 as lat, -72.7107 as long),
        struct('VA' as state_abbr, 'Virginia' as state_name, 37.7693 as lat, -78.1700 as long),
        struct('WA' as state_abbr, 'Washington' as state_name, 47.4009 as lat, -121.4905 as long),
        struct('WV' as state_abbr, 'West Virginia' as state_name, 38.4912 as lat, -80.9545 as long),
        struct('WI' as state_abbr, 'Wisconsin' as state_name, 44.2685 as lat, -89.6165 as long),
        struct('WY' as state_abbr, 'Wyoming' as state_name, 42.7560 as lat, -107.3025 as long)
    ])

), jobs as (

    select
        created_at_utc,
        nullif(trim(job_title), '') as job_title,
        nullif(trim(company_name), '') as company_name,
        nullif(trim(search_term), '') as search_term,
        nullif(trim(job_location), '') as job_location,
        coalesce(nullif(trim(job_platform), ''), data_source, 'Unknown') as job_platform,
        nullif(trim(schedule_type), '') as schedule_type,
        data_source,
        nullif(trim(degree_requirement), '') as degree_requirement,
        job_id,
        nullif(trim(search_location), '') as search_location,
        safe_cast(avg_annual_pay_range as float64) as avg_annual_pay_range,
        cast(removed_date as date) as removed_date,
        cast(posted_date as date) as posted_date,
        coalesce(nullif(trim(listing_status), ''), 'Unknown') as listing_status,
        safe_cast(days_listed as int64) as days_listed,
        safe_cast(opportunity_score as float64) as opportunity_score,
        opportunity_tier,
        job_level
    from `projects-portfolio-446806.reporting.jobs_detail_report`

), state_keyed as (

    select
        jobs.*,
        case
            when regexp_contains(upper(coalesce(job_location, '')), r'\bREMOTE\b') then null
            when regexp_extract(upper(coalesce(job_location, '')), r',\s*([A-Z]{2})(?:\s|,|$)') in (
                'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'
            ) then regexp_extract(upper(coalesce(job_location, '')), r',\s*([A-Z]{2})(?:\s|,|$)')
            when regexp_contains(upper(coalesce(job_location, '')), r'ALABAMA') then 'AL'
            when regexp_contains(upper(coalesce(job_location, '')), r'ALASKA') then 'AK'
            when regexp_contains(upper(coalesce(job_location, '')), r'ARIZONA') then 'AZ'
            when regexp_contains(upper(coalesce(job_location, '')), r'ARKANSAS') then 'AR'
            when regexp_contains(upper(coalesce(job_location, '')), r'CALIFORNIA') then 'CA'
            when regexp_contains(upper(coalesce(job_location, '')), r'COLORADO') then 'CO'
            when regexp_contains(upper(coalesce(job_location, '')), r'CONNECTICUT') then 'CT'
            when regexp_contains(upper(coalesce(job_location, '')), r'DELAWARE') then 'DE'
            when regexp_contains(upper(coalesce(job_location, '')), r'DISTRICT OF COLUMBIA|WASHINGTON DC|WASHINGTON D\.C\.') then 'DC'
            when regexp_contains(upper(coalesce(job_location, '')), r'FLORIDA') then 'FL'
            when regexp_contains(upper(coalesce(job_location, '')), r'GEORGIA') then 'GA'
            when regexp_contains(upper(coalesce(job_location, '')), r'HAWAII') then 'HI'
            when regexp_contains(upper(coalesce(job_location, '')), r'IDAHO') then 'ID'
            when regexp_contains(upper(coalesce(job_location, '')), r'ILLINOIS') then 'IL'
            when regexp_contains(upper(coalesce(job_location, '')), r'INDIANA') then 'IN'
            when regexp_contains(upper(coalesce(job_location, '')), r'IOWA') then 'IA'
            when regexp_contains(upper(coalesce(job_location, '')), r'KANSAS') then 'KS'
            when regexp_contains(upper(coalesce(job_location, '')), r'KENTUCKY') then 'KY'
            when regexp_contains(upper(coalesce(job_location, '')), r'LOUISIANA') then 'LA'
            when regexp_contains(upper(coalesce(job_location, '')), r'MAINE') then 'ME'
            when regexp_contains(upper(coalesce(job_location, '')), r'MARYLAND') then 'MD'
            when regexp_contains(upper(coalesce(job_location, '')), r'MASSACHUSETTS') then 'MA'
            when regexp_contains(upper(coalesce(job_location, '')), r'MICHIGAN') then 'MI'
            when regexp_contains(upper(coalesce(job_location, '')), r'MINNESOTA') then 'MN'
            when regexp_contains(upper(coalesce(job_location, '')), r'MISSISSIPPI') then 'MS'
            when regexp_contains(upper(coalesce(job_location, '')), r'MISSOURI') then 'MO'
            when regexp_contains(upper(coalesce(job_location, '')), r'MONTANA') then 'MT'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEBRASKA') then 'NE'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEVADA') then 'NV'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEW HAMPSHIRE') then 'NH'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEW JERSEY') then 'NJ'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEW MEXICO') then 'NM'
            when regexp_contains(upper(coalesce(job_location, '')), r'NEW YORK') then 'NY'
            when regexp_contains(upper(coalesce(job_location, '')), r'NORTH CAROLINA') then 'NC'
            when regexp_contains(upper(coalesce(job_location, '')), r'NORTH DAKOTA') then 'ND'
            when regexp_contains(upper(coalesce(job_location, '')), r'OHIO') then 'OH'
            when regexp_contains(upper(coalesce(job_location, '')), r'OKLAHOMA') then 'OK'
            when regexp_contains(upper(coalesce(job_location, '')), r'OREGON') then 'OR'
            when regexp_contains(upper(coalesce(job_location, '')), r'PENNSYLVANIA') then 'PA'
            when regexp_contains(upper(coalesce(job_location, '')), r'RHODE ISLAND') then 'RI'
            when regexp_contains(upper(coalesce(job_location, '')), r'SOUTH CAROLINA') then 'SC'
            when regexp_contains(upper(coalesce(job_location, '')), r'SOUTH DAKOTA') then 'SD'
            when regexp_contains(upper(coalesce(job_location, '')), r'TENNESSEE') then 'TN'
            when regexp_contains(upper(coalesce(job_location, '')), r'TEXAS') then 'TX'
            when regexp_contains(upper(coalesce(job_location, '')), r'UTAH') then 'UT'
            when regexp_contains(upper(coalesce(job_location, '')), r'VERMONT') then 'VT'
            when regexp_contains(upper(coalesce(job_location, '')), r'WEST VIRGINIA') then 'WV'
            when regexp_contains(upper(coalesce(job_location, '')), r'VIRGINIA') then 'VA'
            when regexp_contains(upper(coalesce(job_location, '')), r'WASHINGTON') then 'WA'
            when regexp_contains(upper(coalesce(job_location, '')), r'WISCONSIN') then 'WI'
            when regexp_contains(upper(coalesce(job_location, '')), r'WYOMING') then 'WY'
        end as state_abbr
    from jobs

)

select
    state_keyed.*,
    state_centers.state_name,
    state_centers.lat,
    state_centers.long
from state_keyed
left join state_centers using (state_abbr)

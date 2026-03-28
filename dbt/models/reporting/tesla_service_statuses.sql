-- Upcoming, due, and overdue services for each user's vehicles.
-- Based on notification-driven services from tesla_service_timing.
-- Shows the due date or mileage and a status (Upcoming, Due, Overdue).

with vehicles as (

    select
        v.vehicle_id,
        v.user_id,
        u.email,
        v.display_name,
        v.vin
    from {{ ref('dim_tesla_app_vehicles') }} v
    left join {{ ref('dim_tesla_app_users') }} u on u.user_id = v.user_id

),

-- Derive model from vehicle_name in service records (most recent per VIN)
vehicle_model as (

    select vin, vehicle_name,
        case
            when vehicle_name like '%Model3%' then 'Model3'
            when vehicle_name like '%ModelY%' then 'ModelY'
        end as model
    from {{ ref('fact_tesla_service_records') }}
    qualify row_number() over (partition by vin order by completed_date desc) = 1

),

current_odo as (

    select vehicle_id, odo_miles as current_miles
    from {{ ref('fact_tesla_vehicle_info') }}
    qualify row_number() over (partition by vehicle_id order by created_at desc) = 1

),

last_service as (

    select
        vin,
        service_id,
        max(completed_date) as last_service_date,
        max(mileage_stamp) as last_service_miles
    from {{ ref('fact_tesla_service_records') }}
    group by 1, 2

),

timing as (

    select
        safe_cast(service_id as int64) as service_id,
        `desc` as service_desc,
        model,
        reminder_type,
        value_anchor,
        safe_cast(value_anchor as int64) as value_anchor_int
    from {{ ref('tesla_service_timing') }}

),

vehicle_services as (

    select
        v.vehicle_id,
        v.user_id,
        v.email,
        v.display_name,
        v.vin,
        vm.model,
        t.service_id,
        t.service_desc,
        t.reminder_type,
        t.value_anchor,
        t.value_anchor_int,
        ls.last_service_date,
        ls.last_service_miles,
        co.current_miles
    from vehicles v
    inner join vehicle_model vm on vm.vin = v.vin
    inner join timing t on t.model = vm.model
    left join last_service ls
        on ls.vin = v.vin
        and ls.service_id = t.service_id
    left join current_odo co on co.vehicle_id = v.vehicle_id

),

with_due as (

    select
        vehicle_id,
        user_id,
        email,
        display_name,
        vin,
        model,
        service_id,
        service_desc,
        reminder_type,
        current_miles,

        -- Next due mileage (mileage-based only)
        case when reminder_type = 'relative_mileage'
            then coalesce(last_service_miles, 0) + value_anchor_int
            else null
        end as due_at_miles,

        -- Next due date (calendar and relative_days)
        case
            when reminder_type = 'relative_days'
                then date_add(
                    coalesce(last_service_date, current_date),
                    interval value_anchor_int day
                )
            when reminder_type = 'annual'
                then case
                    -- This year's annual date hasn't passed yet → that's the due date
                    when date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    ) > current_date
                    then date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                    -- This year's annual date has passed and service was completed after it → next year
                    when last_service_date >= date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                    then date(
                        extract(year from current_date) + 1,
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                    -- This year's annual date has passed and service was NOT completed → overdue
                    else date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                end
            else null
        end as due_at_date

    from vehicle_services

)

select
    vehicle_id,
    user_id,
    email,
    display_name,
    vin,
    model,
    service_id,
    service_desc,
    reminder_type,
    current_miles,
    due_at_miles,
    due_at_date,

    case
        when reminder_type = 'relative_mileage' then
            case
                when current_miles < due_at_miles then 'Upcoming'
                when current_miles <= due_at_miles + 250 then 'Due'
                else 'Overdue'
            end
        when reminder_type in ('relative_days', 'annual') then
            case
                when due_at_date > current_date then 'Upcoming'
                when due_at_date = current_date then 'Due'
                else 'Overdue'
            end
    end as status

from with_due

order by
    user_id,
    display_name,
    case
        when reminder_type in ('relative_days', 'annual') then due_at_date
        else current_date
    end

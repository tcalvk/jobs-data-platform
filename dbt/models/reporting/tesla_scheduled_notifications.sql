-- All scheduled notifications: one row per vehicle per service.
-- Shows when each notification will fire (date or mileage threshold)
-- and whether it's been sent (today's refresh crossed the threshold).

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

-- Most recent completed service per vehicle + service type
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
        safe_cast(value_anchor as int64) as value_anchor_int,
        safe_cast(notification_offset as int64) as notification_offset_int
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
        t.notification_offset_int,
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

    -- Mileage-based: the mileage at which the notification fires
    case when reminder_type = 'relative_mileage'
        then coalesce(last_service_miles, 0) + value_anchor_int - notification_offset_int
        else null
    end as notify_at_miles,

    -- Mileage-based: the mileage at which service is actually due
    case when reminder_type = 'relative_mileage'
        then coalesce(last_service_miles, 0) + value_anchor_int
        else null
    end as due_at_miles,

    -- Date-based: the date the notification fires
    case
        when reminder_type = 'relative_days'
            then date_add(
                coalesce(last_service_date, date_sub(current_date, interval value_anchor_int day)),
                interval value_anchor_int - notification_offset_int day
            )
        when reminder_type = 'annual'
            then date_sub(
                case
                    when date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    ) >= current_date
                    then date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                    -- If this year's date passed but service was completed after it, use next year
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
                    else date(
                        extract(year from current_date),
                        extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                        extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                    )
                end,
                interval notification_offset_int day
            )
        else null
    end as notify_on_date,

from vehicle_services

where
    -- Mileage-based: notification hasn't fired yet
    (
        reminder_type = 'relative_mileage'
        and current_miles < coalesce(last_service_miles, 0) + value_anchor_int - notification_offset_int
    )
    or
    -- Relative days: notification date is still in the future
    (
        reminder_type = 'relative_days'
        and current_date < date_add(
            coalesce(last_service_date, date_sub(current_date, interval value_anchor_int day)),
            interval value_anchor_int - notification_offset_int day
        )
    )
    or
    -- Annual: notification date is still in the future
    (
        reminder_type = 'annual'
        and current_date < date_sub(
            case
                when date(
                    extract(year from current_date),
                    extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                    extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                ) >= current_date
                then date(
                    extract(year from current_date),
                    extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                    extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                )
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
                else date(
                    extract(year from current_date),
                    extract(month from parse_date('%d-%b-%Y', concat(value_anchor, '-2000'))),
                    extract(day from parse_date('%d-%b-%Y', concat(value_anchor, '-2000')))
                )
            end,
            interval notification_offset_int day
        )
    )

order by
    user_id,
    display_name,
    coalesce(notify_on_date, date('2099-12-31'))

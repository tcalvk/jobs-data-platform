with source as (

    select
        Service_Record_Id as service_record_id,
        VehicleId as vehicle_id,
        Vehicle_Name as vehicle_name,
        VIN as vin,
        ServiceId as service_id,
        Service_Description as service_description,
        CompletedDate as completed_date,
        TotalCost as total_cost,
        MileageStamp as mileage_stamp,
        Notes as notes
    from {{ source('tesla_data_platform', 'service_records') }}

)

select * from source

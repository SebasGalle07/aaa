-- 005_seed_additional_vehicles.sql
-- Agrega vehiculos adicionales de ejemplo a la tabla public.vehicles.

insert into public.vehicles (id, owner_id, make, model, year, vehicle_type, price_per_day, currency, description, location, capacity)
values
    ('44444444-5555-6666-8777-888888888888', 'f799e528-c155-4c18-9515-e7749fc0a136', 'Toyota', 'Corolla', 2020, 'sedan', 65.00, 'USD', 'Sedan confiable y eficiente para uso diario en ciudad.', 'Bogota', 5),
    ('55555555-6666-7777-8888-999999999999', '058b432a-9b65-4dfd-bda0-aa3cc9fc81da', 'Mazda', 'CX-5', 2022, 'suv', 110.00, 'USD', 'SUV mediana con paquete de seguridad i-Activsense.', 'Bogota', 5),
    ('66666666-7777-8888-9999-000000000000', '16347695-1452-407d-9a8d-0ba0a44a8bd9', 'Nissan', 'Kicks', 2021, 'suv', 85.00, 'USD', 'Crossover compacto ideal para recorridos urbanos.', 'Medellin', 5),
    ('77777777-8888-9999-0000-111111111111', 'f799e528-c155-4c18-9515-e7749fc0a136', 'Kia', 'Sportage', 2023, 'suv', 115.00, 'USD', 'SUV con amplio baul y conectividad completa.', 'Cali', 5),
    ('88888888-9999-0000-1111-222222222222', '058b432a-9b65-4dfd-bda0-aa3cc9fc81da', 'Hyundai', 'Tucson', 2022, 'suv', 108.00, 'USD', 'SUV familiar con excelente rendimiento en carretera.', 'Cartagena', 5),
    ('99999999-0000-1111-2222-333333333333', '16347695-1452-407d-9a8d-0ba0a44a8bd9', 'Jeep', 'Compass', 2021, 'suv', 125.00, 'USD', 'Vehiculo con traccion 4x4 para escapadas fuera de la ciudad.', 'Bogota', 5),
    ('aaaaaaa0-bbbb-4ccc-8ddd-eeeeeeeeeeee', 'f799e528-c155-4c18-9515-e7749fc0a136', 'Volkswagen', 'Tiguan', 2022, 'suv', 118.00, 'USD', 'SUV premium con tres filas de asientos.', 'Medellin', 7),
    ('bbbbbbb1-cccc-4ddd-8eee-ffffffffffff', '058b432a-9b65-4dfd-bda0-aa3cc9fc81da', 'Chevrolet', 'Traverse', 2020, 'suv', 130.00, 'USD', 'SUV de gran capacidad, perfecta para viajes en grupo.', 'Barranquilla', 7),
    ('ccccccc2-dddd-4eee-8fff-000000000000', '16347695-1452-407d-9a8d-0ba0a44a8bd9', 'BMW', '330i', 2023, 'sedan', 180.00, 'USD', 'Sedan deportivo con paquete M y asistencia avanzada.', 'Bogota', 5),
    ('ddddddd3-eeee-4fff-8000-111111111111', 'f799e528-c155-4c18-9515-e7749fc0a136', 'Mercedes-Benz', 'GLA 200', 2021, 'suv', 170.00, 'USD', 'SUV compacto premium con interior de lujo.', 'Medellin', 5)
on conflict (id) do nothing;

#!/bin/bash

# Непрерывно слушаем системный D-Bus от BlueZ
dbus-monitor --system "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged'" | while read -r line; do
    
    # Если зафиксирован сигнал подключения устройства
    if echo "$line" | grep -q "Connected"; then
        # Выдерживаем паузу в 1.5 секунды для инициализации аудиовыхода в WirePlumber
        sleep 1.5
        
        # Проверяем готовность системы к воспроизведению, если готова — включаем звук:
        /usr/bin/systemctl restart triggerhappy.service
    fi
done


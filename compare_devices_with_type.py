from extras.scripts import Script
from dcim.models import (
    DeviceType,
    Device,
    Interface,
    ConsolePort,
    PowerPort,
)

class VerifyDeviceTypeComponents(Script):
    """
    Verify that all devices of each Device Type contain the base
    interfaces, console ports, and power ports defined on the Device Type.
    """

    class Meta:
        name = "Verify Device Type vs Device Components"
        description = (
            "Verifies that devices contain all base interfaces, console ports, "
            "and power ports defined on their Device Type. "
            "Extra components are reported as informational only."
        )
        field_order = []

    def run(self, data, commit):

        for device_type in DeviceType.objects.all().order_by("manufacturer__name", "model"):

            base_interfaces = set(
                device_type.interfaces.values_list("name", flat=True)
            )
            base_console_ports = set(
                device_type.console_ports.values_list("name", flat=True)
            )
            base_power_ports = set(
                device_type.power_ports.values_list("name", flat=True)
            )

            devices = Device.objects.filter(device_type=device_type)

            if not devices.exists():
                continue

            self.log_info(
                f"Checking Device Type: {device_type.manufacturer.name} {device_type.model}"
            )

            for device in devices:

                device_interfaces = set(
                    device.interfaces.values_list("name", flat=True)
                )
                device_console_ports = set(
                    device.console_ports.values_list("name", flat=True)
                )
                device_power_ports = set(
                    device.power_ports.values_list("name", flat=True)
                )

                # ---- Missing components (ERROR) ----
                missing_interfaces = base_interfaces - device_interfaces
                missing_console_ports = base_console_ports - device_console_ports
                missing_power_ports = base_power_ports - device_power_ports

                if missing_interfaces or missing_console_ports or missing_power_ports:
                    self.log_failure(
                        f"[{device_type.model}] Device '{device.name}' has missing components"
                    )

                    if missing_interfaces:
                        self.log_failure(
                            f"  Missing interfaces: {sorted(missing_interfaces)}"
                        )

                    if missing_console_ports:
                        self.log_failure(
                            f"  Missing console ports: {sorted(missing_console_ports)}"
                        )

                    if missing_power_ports:
                        self.log_failure(
                            f"  Missing power ports: {sorted(missing_power_ports)}"
                        )

                # ---- Extra components (INFO) ----
                extra_interfaces = device_interfaces - base_interfaces
                extra_console_ports = device_console_ports - base_console_ports
                extra_power_ports = device_power_ports - base_power_ports

                if extra_interfaces:
                    self.log_info(
                        f"[{device_type.model}] Device '{device.name}' has extra interfaces: "
                        f"{sorted(extra_interfaces)}"
                    )

                if extra_console_ports:
                    self.log_info(
                        f"[{device_type.model}] Device '{device.name}' has extra console ports: "
                        f"{sorted(extra_console_ports)}"
                    )

                if extra_power_ports:
                    self.log_info(
                        f"[{device_type.model}] Device '{device.name}' has extra power ports: "
                        f"{sorted(extra_power_ports)}"
                    )

        self.log_success("Device Type component verification completed.")
``

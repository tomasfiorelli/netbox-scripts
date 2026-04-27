#!/opt/netbox/venv/bin/python
import django, os, sys
sys.path.append('/opt/netbox/netbox')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

"""
Compare Device components with DeviceType templates
using deep diffs for interfaces (name + label + type).
"""

from dcim.models import (
    Manufacturer, DeviceType, Device,
    ConsolePort, ConsoleServerPort,
    PowerPort, PowerOutlet,
    Interface, RearPort, FrontPort,
    DeviceBay, ModuleBay,
)
from extras.scripts import Script, ObjectVar, MultiObjectVar


class CompareDeviceWithDeviceTypeDeepDiff(Script):

    class Meta:
        name = "Compare Device With DeviceType (Deep Diff)"
        description = "Compare device components with DeviceType using name, label, and type"

    manufacturer = ObjectVar(
        model=Manufacturer,
        required=False,
    )

    device_type = ObjectVar(
        model=DeviceType,
        query_params={
            "manufacturer_id": "$manufacturer",
        },
        required=False,
    )

    devices = MultiObjectVar(
        model=Device,
        query_params={
            "device_type_id": "$device_type",
        },
    )

    def run(self, data, commit):

        component_map = [
            (ConsolePort, "consoleports", "consoleporttemplates"),
            (ConsoleServerPort, "consoleserverports", "consoleserverporttemplates"),
            (PowerPort, "powerports", "powerporttemplates"),
            (PowerOutlet, "poweroutlets", "poweroutlettemplates"),
            (Interface, "interfaces", "interfacetemplates"),
            (RearPort, "rearports", "rearporttemplates"),
            (FrontPort, "frontports", "frontporttemplates"),
            (DeviceBay, "devicebays", "devicebaytemplates"),
            (ModuleBay, "modulebays", "modulebaytemplates"),
        ]

        for device in data["devices"]:
            dt = device.device_type
            self.log_info(
                f"Comparing device '{device.name}' with DeviceType '{dt.model}'"
            )

            for model, device_attr, template_attr in component_map:
                device_items = getattr(device, device_attr).all()
                template_items = getattr(dt, template_attr).all()

                device_by_name = {i.name: i for i in device_items}
                template_by_name = {t.name: t for t in template_items}

                # Missing & extra (name‑based)
                missing_names = template_by_name.keys() - device_by_name.keys()
                extra_names = device_by_name.keys() - template_by_name.keys()

                # Deep diffs (same name, different attributes)
                drift = []

                for name in device_by_name.keys() & template_by_name.keys():
                    dev = device_by_name[name]
                    tmpl = template_by_name[name]

                    diffs = []

                    # label comparison
                    if getattr(dev, "label", None) != getattr(tmpl, "label", None):
                        diffs.append(
                            f"label: device='{dev.label}' | template='{tmpl.label}'"
                        )

                    # type comparison (choices -> compare raw value)
                    if getattr(dev, "type", None) != getattr(tmpl, "type", None):
                        diffs.append(
                            f"type: device='{dev.type}' | template='{tmpl.type}'"
                        )

                    if diffs:
                        drift.append((name, diffs))

                if not missing_names and not extra_names and not drift:
                    continue

                for name in sorted(missing_names):
                    self.log_warning(f"MISSING > {device_attr} > {name}")

                for name in sorted(extra_names):
                    self.log_warning(f"EXTRA > {device_attr} > {name}")

                for name, diffs in drift:
                    for diff in diffs:
                        self.log_warning(
                            f"DIFF > {device_attr} > {name} > {diff}"
                        )

            self.log_success(f"Comparison finished for {device.name}")
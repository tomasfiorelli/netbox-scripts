"""
Create missing device components from DeviceType templates
and update existing components with missing attributes.
"""

from dcim.models import (
    Manufacturer, DeviceType, Device,
    ConsolePort, ConsoleServerPort,
    PowerPort, PowerOutlet,
    Interface, RearPort, FrontPort,
    DeviceBay, ModuleBay,
)
from extras.scripts import Script, ObjectVar, MultiObjectVar


class SyncDeviceFromDeviceType(Script):

    class Meta:
        name = "Sync Device Components from DeviceType"
        description = (
            "Create missing components and update existing ones "
            "based on the DeviceType definition"
        )

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
            # class, device attr, template attr
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
                f"Syncing device '{device.name}' from DeviceType '{dt.model}'"
            )

            for model, device_attr, template_attr in component_map:
                device_items = list(getattr(device, device_attr).all())
                template_items = list(getattr(dt, template_attr).all())

                # Index device objects by lowercase name (for case-insensitive match)
                device_by_name_ci = {
                    d.name.lower(): d for d in device_items
                }

                for tmpl in template_items:
                    tmpl_name_lc = tmpl.name.lower()

                    # Case 1: Component does not exist → CREATE
                    if tmpl_name_lc not in device_by_name_ci:
                        obj = tmpl.instantiate(device=device)
                        obj.full_clean()
                        obj.save()
                        self.log_success(
                            f"CREATED {device_attr}: {tmpl.name}"
                        )
                        continue

                    # Case 2: Component exists → UPDATE IF NEEDED
                    obj = device_by_name_ci[tmpl_name_lc]
                    updated = False

                    # Fix capitalization
                    if obj.name != tmpl.name:
                        old_name = obj.name
                        obj.name = tmpl.name
                        updated = True
                        self.log_info(
                            f"RENAMED {device_attr}: '{old_name}' → '{tmpl.name}'"
                        )

                    # Copy label if missing
                    if hasattr(obj, "label"):
                        if not obj.label and tmpl.label:
                            obj.label = tmpl.label
                            updated = True

                    # Interface-specific fields
                    if isinstance(obj, Interface):
                        if obj.type != tmpl.type:
                            obj.type = tmpl.type
                            updated = True

                    # PowerPort-specific fields
                    if isinstance(obj, PowerPort):
                        if (
                            hasattr(tmpl, "maximum_draw")
                            and obj.maximum_draw is None
                            and tmpl.maximum_draw is not None
                        ):
                            obj.maximum_draw = tmpl.maximum_draw
                            updated = True

                        if (
                            hasattr(tmpl, "allocated_draw")
                            and obj.allocated_draw is None
                            and tmpl.allocated_draw is not None
                        ):
                            obj.allocated_draw = tmpl.allocated_draw
                            updated = True

                    if updated:
                        obj.full_clean()
                        obj.save()
                        self.log_success(
                            f"UPDATED {device_attr}: {obj.name}"
                        )

            self.log_success(f"Sync completed for {device.name}")
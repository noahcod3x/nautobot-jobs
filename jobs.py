import csv
from io import StringIO

from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device


name = "Training Lab"


class WorkstationCablingAudit(Job):
    class Meta:
        name = "Workstation Cabling Audit"
        description = "Audit training workstations and produce a CSV cabling report."
        read_only = True
        has_sensitive_variables = False

    def run(self):
        workstations = Device.objects.filter(
            role__name="Workstation",
            tags__name="training-lab",
        ).order_by("name")

        passed = 0
        failed = 0
        report_rows = []

        for device in workstations:
            cabled_interfaces = [
                interface.name
                for interface in device.interfaces.all()
                if getattr(interface, "cable", None)
            ]

            log_context = {
                "grouping": "cabling-audit",
                "object": device,
            }

            if cabled_interfaces:
                result = "PASS"
                interface_names = ", ".join(cabled_interfaces)

                self.logger.success(
                    "%s has cabled interface(s): %s",
                    device.name,
                    interface_names,
                    extra=log_context,
                )
                passed += 1
            else:
                result = "FAIL"
                interface_names = ""

                self.logger.failure(
                    "%s has no cabled interface",
                    device.name,
                    extra=log_context,
                )
                failed += 1

            report_rows.append(
                {
                    "device": device.name,
                    "result": result,
                    "cabled_interfaces": interface_names,
                }
            )

        csv_output = StringIO()
        writer = csv.DictWriter(
            csv_output,
            fieldnames=["device", "result", "cabled_interfaces"],
        )
        writer.writeheader()
        writer.writerows(report_rows)

        self.create_file(
            "workstation_cabling_audit.csv",
            csv_output.getvalue(),
        )

        self.logger.info(
            "Audit complete: %s passed, %s failed. CSV report created.",
            passed,
            failed,
            extra={"grouping": "summary"},
        )

        if failed:
            self.fail(f"{failed} workstation(s) have no cabled interface.")

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
        }

class PrimaryIPAddressAudit(Job):
    class Meta:
        name = "Primary IPv4 Address Audit"
        description = "Check training devices for an assigned primary IPv4 address."
        read_only = True
        has_sensitive_variables = False

    def run(self):
        devices = (
            Device.objects.filter(tags__name="training-lab")
            .distinct()
            .order_by("name")
        )

        passed = 0
        failed = 0
        report_rows = []

        for device in devices:
            primary_ip = device.primary_ip4
            log_context = {
                "grouping": "primary-ip-audit",
                "object": device,
            }

            if primary_ip:
                result = "PASS"
                address = str(primary_ip)

                self.logger.success(
                    "%s has primary IPv4 address %s",
                    device.name,
                    address,
                    extra=log_context,
                )
                passed += 1
            else:
                result = "FAIL"
                address = ""

                self.logger.failure(
                    "%s has no primary IPv4 address",
                    device.name,
                    extra=log_context,
                )
                failed += 1

            report_rows.append(
                {
                    "device": device.name,
                    "result": result,
                    "primary_ip4": address,
                }
            )

        csv_output = StringIO()
        writer = csv.DictWriter(
            csv_output,
            fieldnames=["device", "result", "primary_ip4"],
        )
        writer.writeheader()
        writer.writerows(report_rows)

        self.create_file(
            "primary_ipv4_audit.csv",
            csv_output.getvalue(),
        )

        self.logger.info(
            "Primary IPv4 audit complete: %s passed, %s failed.",
            passed,
            failed,
            extra={"grouping": "summary"},
        )

        if failed:
            self.fail(f"{failed} device(s) have no primary IPv4 address.")

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
        }


register_jobs(WorkstationCablingAudit, PrimaryIPAddressAudit)

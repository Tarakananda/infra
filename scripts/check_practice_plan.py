#!/usr/bin/env python3
"""Check the reviewed dev capacity profile, not the usage-dependent AWS bill.

Usage: terraform show -json tfplan | python3 ../../scripts/check_practice_plan.py
The plan contains secrets: consume stdin and never echo its values.
"""
from datetime import date
import json
import sys

VERSION = "1.36"
STANDARD_SUPPORT_END = date(2027, 8, 2)


def resources(module):
    yield from (r for r in module.get("resources", []) if r.get("mode") == "managed")
    for child in module.get("child_modules", []):
        yield from resources(child)


def check_plan(plan, today=None):
    errors = []
    items = list(resources(plan.get("planned_values", {}).get("root_module", {})))

    def expect(condition, message):
        if not condition:
            errors.append(message)

    def exactly_one(kind):
        found = [r["values"] for r in items if r["type"] == kind]
        expect(len(found) == 1, f"Expected exactly one {kind}.")
        return found[0] if len(found) == 1 else {}

    region = plan.get("configuration", {}).get("provider_config", {}).get("aws", {}).get("expressions", {}).get("region", {}).get("constant_value")
    expect(region == "ap-south-1", "Use the reviewed ap-south-1 region.")
    cluster = exactly_one("aws_eks_cluster")
    expect(cluster.get("name") == "pharma-dev-cluster", "Only the dev cluster is allowed.")
    expect(cluster.get("version") == VERSION, f"Review support dates and pricing before changing EKS {VERSION}.")
    expect((today or date.today()) < STANDARD_SUPPORT_END, "EKS version support review is due; update the practice profile before applying.")
    expect(cluster.get("upgrade_policy") == [{"support_type": "STANDARD"}], "EKS extended support must be disabled.")
    expect(not cluster.get("enabled_cluster_log_types"), "Control-plane log ingestion is outside this practice estimate.")
    nodes = exactly_one("aws_eks_node_group")
    expect(nodes.get("instance_types") == ["m7i-flex.large"], "Use one m7i-flex.large worker.")
    expect(nodes.get("capacity_type") == "ON_DEMAND", "The estimate uses on-demand workers.")
    expect(nodes.get("scaling_config") == [{"desired_size": 1, "min_size": 1, "max_size": 1}], "Worker min/desired/max must all be one.")
    update = nodes.get("update_config") or [{}]
    expect(update[0].get("update_strategy") == "MINIMAL", "Use MINIMAL node updates to avoid temporary surge capacity.")
    launch = exactly_one("aws_launch_template")
    expect(not launch.get("credit_specification"), "Do not set T-series CPU credits on an M7i-flex worker.")
    disks = launch.get("block_device_mappings") or []
    disk = (disks[0].get("ebs") or [{}])[0] if len(disks) == 1 else {}
    expect(disk.get("volume_size") == 20 and disk.get("volume_type") == "gp3", "Use one 20 GiB gp3 worker disk.")
    db = exactly_one("aws_db_instance")
    expect(db.get("identifier") == "pharma-dev-postgres", "Only the dev database is allowed.")
    expect(db.get("instance_class") == "db.t3.micro" and db.get("multi_az") is False, "Use single-AZ db.t3.micro.")
    expect(db.get("allocated_storage") == 20 and db.get("max_allocated_storage") == 0 and db.get("storage_type") == "gp3", "RDS must use 20 GiB gp3 without storage autoscaling.")
    expect(db.get("backup_retention_period") == 1, "Keep the account-compatible one-day RDS backup retention.")
    expect(db.get("publicly_accessible") is False, "The practice database stays private.")
    exactly_one("aws_nat_gateway")
    exactly_one("aws_eip")
    forbidden = {"aws_instance", "aws_autoscaling_group", "aws_eks_fargate_profile", "aws_eks_capability",
                 "aws_lb", "aws_alb", "aws_elb", "aws_ebs_volume", "aws_efs_file_system",
                 "aws_rds_cluster", "aws_rds_cluster_instance", "aws_cloudwatch_log_group"}
    for item in items:
        expect(item["type"] not in forbidden, f"Unreviewed billable resource type: {item['type']}.")
        if item["type"] == "aws_vpc_endpoint":
            expect(item["values"].get("vpc_endpoint_type") == "Gateway", "Paid interface endpoints are outside the estimate.")
    expect(sum(r["type"] == "aws_ecr_repository" for r in items) <= 9, "Review registry storage before adding more repositories.")
    # Catch accidental dev replacements and upgrades AWS cannot apply directly.
    for change in plan.get("resource_changes", []):
        actions = change.get("change", {}).get("actions", [])
        if change["type"] == "aws_eks_cluster" and actions == ["update"]:
            before = change["change"].get("before", {}).get("version")
            after = change["change"].get("after", {}).get("version")
            if before and after and before != after:
                expect(int(after.split(".")[1]) - int(before.split(".")[1]) == 1,
                       "An existing EKS cluster must be upgraded one minor at a time; review the migration before applying.")
        if "create" in actions and "delete" in actions and change["type"] in {
                "aws_eks_cluster", "aws_eks_node_group", "aws_db_instance", "aws_nat_gateway"}:
            errors.append(f"Review replacement and temporary cost before applying {change['address']}.")
    return errors


def main():
    errors = check_plan(json.load(sys.stdin))
    if errors:
        for error in errors:
            print("Practice profile check failed: " + error, file=sys.stderr)
        return 1
    print("Practice capacity checks passed. Estimated idle baseline: about $0.30/hour before tax.")
    print("Traffic, RDS CPU credits, registry/storage/API usage and other account resources are additional; this is not a billing cap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

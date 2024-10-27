from datetime import datetime, timedelta
from uuid import uuid4

from django.core.management.base import BaseCommand
import sys
import json

from domovoy.apps.dmv_home.models import Home, Membership
from domovoy.apps.dmv_user.models import DmvUser
from domovoy.apps.regular_job import rules
from domovoy.apps.regular_job.models import RegularJobDefinition, RegularJobInstance
from domovoy.apps.regular_job.utils import before_midnight


def get_rules(definition):
    rule_list = []
    rule_list.append(
        rules.RuleDelay(
            **{
                definition["fields"]["frequency_unit"] + "s": definition["fields"][
                    "frequency"
                ]
            }
        )
    )
    if definition["fields"]["season_begins"] or definition["fields"]["season_ends"]:
        date_iter = datetime.fromisoformat(definition["fields"]["season_begins"])
        date_end = datetime.fromisoformat(definition["fields"]["season_ends"])

        months = set()
        while date_iter.isoformat()[5:10] != date_end.isoformat()[5:10]:
            date_iter += timedelta(days=1)
            months.add(date_iter.strftime(rules.CalendarQuery.MONTH_NAME.value))
        rule_list.append(
            rules.RuleCalendar(
                query=rules.CalendarQuery.MONTH_NAME, match=list(months)
            )
        )
        print(list(months))

    weekdays = set()
    for k, v in definition["fields"].items():
        if k.startswith("weekday") and v:
            weekdays.add(k.split("_")[2].title())
    if len(weekdays) < 7:
        rule_list.append(
            rules.RuleCalendar(
                query=rules.CalendarQuery.WEEKDAY_NAME, match=list(weekdays)
            )
        )

    return rules.Ruleset(rules=rule_list)


class Command(BaseCommand):
    help = "Migrates data from the previous iteration of the system"

    def create_users(self, data, migration_map):
        for user in data:
            result, created = DmvUser.objects.get_or_create(
                username=user["fields"]["email"],
                defaults={
                    "email": user["fields"]["email"],
                    "name_full": user["fields"]["first_name"]
                    + " "
                    + user["fields"]["last_name"],
                    "name_short": user["fields"]["first_name"],
                    "email_verified": True
                },
            )
            migration_map[("user", user["pk"])] = result
            if created:
                password = str(uuid4())
                result.set_password(password)
                result.save()
                print("Created user", result.username, password)
        return migration_map

    def create_homes(self, data, migration_map):
        for home in data:
            result, created = Home.objects.get_or_create(
                name=home["fields"]["name"],
                defaults={"description": home["fields"]["location"]},
            )
            migration_map[("home", home["pk"])] = result

    def create_memberships(self, data, migration_map):
        for membership in data:
            home = migration_map[("home", membership["fields"][self.entity])]
            user = migration_map[("user", membership["fields"]["user"])]
            result, created = Membership.objects.get_or_create(
                user=user,
                home=home,
                defaults={"score": membership["fields"]["unspent_credits"]},
            )
            migration_map[("membership", membership["pk"])] = result

    def create_job_definitions(self, data, migration_map):
        for jd in data:
            result, created = RegularJobDefinition.objects.get_or_create(
                home=migration_map[("home", jd["fields"][self.entity])],
                name=jd["fields"]["name"],
                defaults={
                    "description": jd["fields"]["name"],
                    "value_min": jd["fields"]["credits"],
                    "value_max": jd["fields"]["credits"],
                    "value_default": jd["fields"]["credits"],
                    "open_for_days": 7,
                    "criticality": "M",
                    "rules": get_rules(jd).model_dump(mode="json"),
                    "assignment_notes": None,
                    "next_assigned_to": None,
                    "next_assigned_date": None,
                    "next_assigned_start_date": None,
                    "next_assigned_due_date": None,
                },
            )
            migration_map[("job_definition", jd["pk"])] = result

    def create_job_instances(self, instances, resolutions, migration_map):
        for instance in instances:
            definition = migration_map[("job_definition", instance["fields"]["job"])]
            membership = migration_map[("membership", instance["fields"]["sentence"])]
            if instance["fields"]["resolution"] is None:
                definition.assignment_notes = None
                definition.next_assigned_to = membership.user
                definition.next_assigned_date = instance["fields"]["assigned"]
                definition.next_assigned_start_date = datetime.fromisoformat(
                    instance["fields"]["due"]
                ) - timedelta(days=7)
                definition.next_assigned_due_date = before_midnight(datetime.fromisoformat(
                    instance["fields"]["due"]
                ))
                definition.save()
            elif "Done" in resolutions[instance["fields"]["resolution"]]:
                membership = migration_map[
                    ("membership", instance["fields"]["sentence"])
                ]
                job_definition = migration_map[
                    ("job_definition", instance["fields"]["job"])
                ]

                RegularJobInstance.objects.get_or_create(
                    job=job_definition,
                    value=job_definition.value_default,
                    completed_by=membership.user,
                    completed_at=instance["fields"]["completed"],
                    defaults={
                        "assigned_at": instance["fields"]["assigned"],
                        "can_start_at": datetime.fromisoformat(
                            instance["fields"]["due"]
                        )
                        - timedelta(days=7),
                        "due_at": instance["fields"]["due"],
                    },
                )

    def handle(self, *args, **options):
        raw_data = sys.stdin.read()
        data = json.loads(raw_data)

        migration_map = {}

        self.entity = [_ for _ in data if "location" in _["fields"]][0]["model"].split(
            "."
        )[0]

        self.create_users([_ for _ in data if _["model"] == "auth.user"], migration_map)
        self.create_homes(
            [_ for _ in data if _["model"] == f"{self.entity}.{self.entity}"],
            migration_map,
        )
        self.create_memberships(
            [_ for _ in data if _["model"] == "worker.sentence"], migration_map
        )
        self.create_job_definitions(
            [_ for _ in data if _["model"] == "job.job"], migration_map
        )
        task_definition_lookup = {}
        for object in data:
            if object["model"] == "task.taskresolution":
                task_definition_lookup[object["pk"]] = object["fields"]["name"]
        self.create_job_instances(
            [_ for _ in data if _["model"] == "task.task"],
            task_definition_lookup,
            migration_map,
        )

        print({_["model"] for _ in data})

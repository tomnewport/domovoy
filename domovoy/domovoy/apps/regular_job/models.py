import datetime
from datetime import timedelta
from random import randrange, random
from typing import Optional

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from domovoy.apps.dmv_home.models import Home
from domovoy.apps.regular_job.rules import (
    Ruleset,
    generate_dates,
    RuleComputeResult,
    RuleComputeResultParticipant,
    CriticalityLevel,
    SnoozeOption,
)
from domovoy.apps.regular_job.utils import before_midnight

User = get_user_model()


class RegularJobDefinition(models.Model):
    home = models.ForeignKey(
        to=Home, on_delete=models.CASCADE, related_name="regular_jobs"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    value_max = models.PositiveSmallIntegerField()
    value_min = models.PositiveSmallIntegerField()
    value_default = models.PositiveSmallIntegerField()

    open_for_days = models.PositiveSmallIntegerField(default=0)
    criticality = models.CharField(
        max_length=1, choices=CriticalityLevel.choices, default=CriticalityLevel.LOW
    )
    rules = models.JSONField(default=dict)
    assignment_notes = models.JSONField(null=True, blank=True)

    next_assigned_to = models.ForeignKey(
        to=User, on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    next_assigned_date = models.DateTimeField(blank=True, null=True)
    next_assigned_start_date = models.DateTimeField(blank=True, null=True)
    next_assigned_due_date = models.DateTimeField(blank=True, null=True)

    @property
    def days_overdue(self):
        if not self.next_assigned_due_date:
            return 0
        return (timezone.now() - self.next_assigned_due_date).days

    @property
    def bonus(self):
        if self.home.overdue_bounty == 0:
            return 0
        if self.open_for_days == 0:
            return 0
        max_bonus = self.value_default * 10
        return min(max_bonus, int(self.value_default * (max(0, int(self.days_overdue)) / self.open_for_days) * (self.home.overdue_bounty / 100)))

    def snooze_options(self) -> list[SnoozeOption]:
        if not self.next_assigned_due_date:
            return []
        # Each skip is the next ideal date after the previous one, starting
        # from the current due date.
        skips = [self.assign(override_date=self.next_assigned_due_date.date())]
        if skips[0] is None:  # no rules, so no schedule to skip along
            return []
        for _ in range(6):
            skips.append(self.assign(override_date=skips[-1].ideal_date))

        today = timezone.now().date()

        options = [
            SnoozeOption(date=v.ideal_date, label=f"Skip +{i+1}")
            for i, v in enumerate(skips)
        ]
        options.append(SnoozeOption(date=today + timedelta(days=1), label="Tomorrow"))
        options.append(SnoozeOption(date=today + timedelta(days=2), label="+2 days"))
        options.append(SnoozeOption(date=today + timedelta(days=7), label="+1 week"))

        dates = set()

        filtered = [_ for _ in options if _.date > today and _.date > self.next_assigned_due_date.date()]
        unique = []
        for _ in filtered:
            if _.date not in dates:
                unique.append(_)
            dates.add(_.date)

        return sorted(unique, key=lambda _: _.date)

    def assign(self, preserve_member = False, override_date: Optional[datetime.date] = None):
        """
        Assignees:
           Each assignee rolls a number of D6 dice - controlled by the home's rules.
               home.d6_cost => number of minutes to earn an extra d6
               home.d6_min => number of dice all members get to roll
               home.d6_max => maximum number of dice a member can have
            Lowest score does the task

        Holidays:
           L: Assign to whoever has the job, after back from holiday (plus random buffer)
           M: Assign to whoever is around, if assignee is on holiday, or L if not possible
           H: Assign to whoever is around, as close to ideal date before holiday
        """
        solution = RuleComputeResult()
        rules = Ruleset.parse_obj(self.rules)
        baseline = override_date or timezone.now().date()
        if not len(rules.rules):
            return None
        all_members = self.home.memberships.all()
        for assignee in all_members:
            n_dice = max(
                min(assignee.score // self.home.d6_cost, self.home.d6_max),
                self.home.d6_min,
            )
            rolls = [randrange(1, 7) for _ in range(n_dice)]
            if preserve_member and assignee.user_id == self.next_assigned_to_id:
                # Rolls 0 to keep same assignee
                rolls = [0]
            tiebreak = random()
            calculator = rules.find(baseline)
            assignee_date = next(assignee.filter_available_dates(calculator))
            solution.participants.append(
                RuleComputeResultParticipant(
                    user_id=assignee.user.id,
                    user_name=assignee.user.name_full,
                    score=assignee.score,
                    rolls=rolls,
                    tiebreak=tiebreak,
                    first_available=assignee_date,
                )
            )

        solution.participants = sorted(
            solution.participants, key=lambda _: sum(_.rolls) + _.tiebreak
        )
        solution.ideal_date = next(rules.find(baseline))

        for participant in solution.participants:
            if (
                participant.first_available == solution.ideal_date
                or self.criticality == CriticalityLevel.LOW
            ):
                solution.assignee = participant.user_id
                solution.selected_date = participant.first_available
                solution.remark = (
                    "Perfect"
                    if participant.first_available == solution.ideal_date
                    else "Job can be delayed"
                )
                return solution

        if self.criticality == CriticalityLevel.MEDIUM:
            selected = min(solution.participants, key=lambda _: _.first_available)
            solution.assignee = selected.user_id
            solution.selected_date = selected.first_available
            solution.remark = (
                "Switched due to availability"
                if solution.selected_date == solution.ideal_date
                else "Closest available"
            )
            return solution

        # High-criticality follows Price is Right rules - as close to the date without going over
        best_solution = None
        for assignee in all_members:
            all_dates = generate_dates(baseline)
            for candidate_date in assignee.filter_available_dates(all_dates):
                if candidate_date > solution.ideal_date:
                    break
                if best_solution is None or best_solution[0] < candidate_date:
                    best_solution = (candidate_date, assignee)

        if best_solution is None:
            solution.assignee = solution.participants[0].user_id
            solution.selected_date = solution.participants[0].first_available
            solution.remark = "Failed to find a good date"
            return solution
        else:
            solution.assignee = best_solution[1].user_id
            solution.selected_date = best_solution[0]
            solution.remark = "Scheduled before holiday"
            return solution

    def validate_value(self, value: Optional[int] = None):
        with_default = value or self.value_default
        if with_default > self.value_max:
            return self.value_max
        if with_default < self.value_min:
            return self.value_min
        return with_default

    def claim(self, user: User, value: Optional[int] = None):
        bonus = 0
        if user != self.next_assigned_to:
            bonus = self.bonus
        with transaction.atomic():
            # First off - increment the user's score. Also find the min score
            total_value = self.validate_value(value) + bonus
            all_memberships = self.home.memberships.all()
            min_score = 10**20
            for membership in all_memberships:
                if membership.user == user:
                    membership.score += total_value
                min_score = min(min_score, membership.score)

            # Now normalise - making the lowest score 0
            for membership in all_memberships:
                membership.score -= min_score
                membership.save()

            self.home.base_score += min_score
            self.home.save()
            
            # Create instance
            instance = RegularJobInstance(
                job=self,
                value=total_value,
                completed_by=user,
                assigned_at=self.next_assigned_date,
                can_start_at=self.next_assigned_start_date,
                due_at=self.next_assigned_due_date,
                completed_at=timezone.now(),
            )
            instance.save()

            # Cancel next assignment
            self.next_assigned_to = None
            self.next_assigned_date = None
            self.next_assigned_start_date = None
            self.next_assigned_due_date = None
            self.assignment_notes = None
            self.save()

        solution = self.assign()
        if solution:
            self.next_assigned_to = User.objects.get(id=solution.assignee)
            self.next_assigned_date = timezone.now()
            self.next_assigned_due_date = before_midnight(
                solution.selected_date
            )
            self.next_assigned_start_date = max(
                self.next_assigned_date + timedelta(hours=1),
                self.next_assigned_due_date - timedelta(days=self.open_for_days)
            )
            self.assignment_notes = solution.model_dump(mode="json")
            self.save()
        return total_value

    def adjust(self):
        if self.next_assigned_date:
            override_date = self.next_assigned_date.date()
        else:
            override_date = None
        solution = self.assign(preserve_member=True, override_date=override_date)
        if solution:
            self.next_assigned_to = User.objects.get(id=solution.assignee)
            self.next_assigned_date = timezone.now()
            self.next_assigned_due_date = before_midnight(
                solution.selected_date
            )
            self.next_assigned_start_date = max(
                self.next_assigned_date + timedelta(hours=1),
                self.next_assigned_due_date - timedelta(days=self.open_for_days)
            )
            self.assignment_notes = solution.model_dump(mode="json")
        else:
            self.next_assigned_to = None
            self.next_assigned_due_date = None
            self.next_assigned_date = None
            self.next_assigned_start_date = None
            self.assignment_notes = None
        self.save()


class RegularJobInstance(models.Model):
    job = models.ForeignKey(
        to=RegularJobDefinition, on_delete=models.CASCADE, related_name="instances"
    )
    value = models.PositiveSmallIntegerField()
    completed_by = models.ForeignKey(
        to=User, on_delete=models.PROTECT, related_name="regular_jobs"
    )

    assigned_at = models.DateTimeField(blank=True, null=True)
    can_start_at = models.DateTimeField(blank=True, null=True)
    due_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

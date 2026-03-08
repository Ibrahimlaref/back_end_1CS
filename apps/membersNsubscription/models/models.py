import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone   
from .gym import Gym
from apps.users.models.user import User, CoachProfile
# ─── SUBSCRIPTIONS ────────────────────────────────────────────────────────────

class MembershipPlan(models.Model):
    class Type(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"
        SESSION_PACK = "session_pack", "Session Pack"
        TRIAL = "trial", "Trial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="membership_plans")
    name = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    duration_days = models.IntegerField(null=True, blank=True)
    session_limit = models.IntegerField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "membership_plans"

    def __str__(self):
        return f"{self.name} ({self.gym})"


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="subscriptions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    remaining_sessions = models.IntegerField(null=True, blank=True)
    pause_days_used = models.IntegerField(default=0)
    paused_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscriptions"

    def __str__(self):
        return f"Subscription: {self.user} @ {self.gym} ({self.status})"


class SubscriptionPause(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="pauses")
    pause_start = models.DateTimeField()
    pause_end = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscription_pauses"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        ONLINE = "online", "Online"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(
        Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reference = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment: {self.amount} {self.currency} ({self.status})"


# ─── SCHEDULING ───────────────────────────────────────────────────────────────

class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="rooms")
    name = models.TextField()
    capacity = models.SmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "rooms"

    def __str__(self):
        return f"{self.name} @ {self.gym}"


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL_LEVELS = "all_levels", "All Levels"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="courses")
    coach = models.ForeignKey(CoachProfile, on_delete=models.PROTECT, related_name="courses")
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="courses")
    title = models.TextField()
    description = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.ALL_LEVELS)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    max_participants = models.SmallIntegerField()
    is_cancelled = models.BooleanField(default=False)
    cancellation_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "courses"

    def __str__(self):
        return f"{self.title} @ {self.gym} ({self.start_time})"


class Reservation(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        CANCELLED = "cancelled", "Cancelled"
        ATTENDED = "attended", "Attended"
        NO_SHOW = "no_show", "No Show"
        WAITLISTED = "waitlisted", "Waitlisted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="reservations")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    waitlist_pos = models.SmallIntegerField(null=True, blank=True)
    reserved_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    attended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reservations"
        unique_together = [("course", "user")]

    def __str__(self):
        return f"Reservation: {self.user} → {self.course} ({self.status})"


# ─── GYM OPERATIONS ───────────────────────────────────────────────────────────

class Equipment(models.Model):
    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        MAINTENANCE_NEEDED = "maintenance_needed", "Maintenance Needed"
        UNDER_MAINTENANCE = "under_maintenance", "Under Maintenance"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="equipment")
    name = models.TextField()
    serial_number = models.TextField(blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPERATIONAL)
    purchased_at = models.DateField(null=True, blank=True)
    last_maintenance = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "equipment"

    def __str__(self):
        return f"{self.name} ({self.status})"


class MaintenanceReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="maintenance_reports")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="maintenance_reports")
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reported_maintenance")
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_maintenance"
    )
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_reports"


class Warning(models.Model):
    class Type(models.TextChoices):
        NO_SHOW = "no_show", "No Show"
        MISCONDUCT = "misconduct", "Misconduct"
        PAYMENT = "payment", "Payment"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="warnings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="members_warnings")
    issued_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="members_issued_warnings")
    reason = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "members_warnings"

    def __str__(self):
        return f"Warning: {self.user} ({self.type})"


# ─── COMMERCE ─────────────────────────────────────────────────────────────────

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="products")
    name = models.TextField()
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="orders")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.SmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"


# ─── ENGAGEMENT ───────────────────────────────────────────────────────────────

class Notification(models.Model):
    class Type(models.TextChoices):
        COURSE_REMINDER = "course_reminder", "Course Reminder"
        SUBSCRIPTION_RENEWAL = "subscription_renewal", "Subscription Renewal"
        WARNING_ISSUED = "warning_issued", "Warning Issued"
        PROMOTION = "promotion", "Promotion"
        GENERAL = "general", "General"
        RECOMMENDATION = "recommendation", "Recommendation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="members_notifications")
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.TextField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "members_notifications"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"

    def __str__(self):
        return f"Message: {self.sender} → {self.receiver}"


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_logs")
    activity_type = models.TextField()
    calories_burned = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    duration_minutes = models.SmallIntegerField(null=True, blank=True)
    activity_date = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "activity_logs"


# ─── SYSTEM LOGS ──────────────────────────────────────────────────────────────


# ─── BEHAVIORAL ANALYTICS ─────────────────────────────────────────────────────

class MemberBehaviorEvent(models.Model):
    class EventType(models.TextChoices):
        COURSE_VIEWED = "course_viewed", "Course Viewed"
        COURSE_BOOKED = "course_booked", "Course Booked"
        COURSE_CANCELLED = "course_cancelled", "Course Cancelled"
        COURSE_ATTENDED = "course_attended", "Course Attended"
        COURSE_NO_SHOW = "course_no_show", "Course No Show"
        COACH_VIEWED = "coach_viewed", "Coach Viewed"
        EQUIPMENT_USED = "equipment_used", "Equipment Used"
        PRODUCT_VIEWED = "product_viewed", "Product Viewed"
        PRODUCT_PURCHASED = "product_purchased", "Product Purchased"
        PLAN_VIEWED = "plan_viewed", "Plan Viewed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="behavior_events")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="behavior_events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    entity_type = models.TextField(blank=True)
    entity_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "member_behavior_events"
        indexes = [
            models.Index(fields=["gym", "user", "event_type"]),
            models.Index(fields=["occurred_at"]),
        ]


class CourseInterestScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="course_interest_scores")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_interest_scores")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="interest_scores")
    view_count = models.IntegerField(default=0)
    booked_count = models.IntegerField(default=0)
    attended_count = models.IntegerField(default=0)
    cancelled_count = models.IntegerField(default=0)
    no_show_count = models.IntegerField(default=0)
    interest_score = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_interest_scores"
        unique_together = [("gym", "user", "course")]


class MemberPreference(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL_LEVELS = "all_levels", "All Levels"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="member_preferences")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="member_preferences")
    preferred_level = models.CharField(max_length=20, choices=Level.choices, null=True, blank=True)
    preferred_days = ArrayField(models.TextField(), default=list, blank=True)
    preferred_times = ArrayField(models.TextField(), default=list, blank=True)
    preferred_coach_ids = ArrayField(models.UUIDField(), default=list, blank=True)
    disliked_course_types = ArrayField(models.TextField(), default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "member_preferences"
        unique_together = [("gym", "user")]


class CoachPerformance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="coach_performances")
    coach = models.ForeignKey(CoachProfile, on_delete=models.CASCADE, related_name="performance_records")
    period_month = models.DateField()  # Store as first day of month
    total_courses = models.IntegerField(default=0)
    total_reservations = models.IntegerField(default=0)
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    no_show_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    avg_participants = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "coach_performances"
        unique_together = [("gym", "coach", "period_month")]


class CoursePopularity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="course_popularity")
    course_title = models.TextField()
    level = models.TextField(blank=True)
    coach = models.ForeignKey(
        CoachProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="popularity_records"
    )
    total_runs = models.IntegerField(default=0)
    avg_fill_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    total_attendees = models.IntegerField(default=0)
    no_show_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    peak_day_of_week = models.SmallIntegerField(null=True, blank=True)  # 0=Monday, 6=Sunday
    peak_hour = models.SmallIntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_popularity"


class MemberRetentionSignal(models.Model):
    class Signal(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        AT_RISK = "at_risk", "At Risk"
        CHURNING = "churning", "Churning"
        CHURNED = "churned", "Churned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="retention_signals")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="retention_signals")
    days_since_last_visit = models.IntegerField(default=0)
    bookings_last_30_days = models.IntegerField(default=0)
    bookings_prev_30_days = models.IntegerField(default=0)
    attendance_rate_last_30 = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    churn_risk_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    signal = models.CharField(max_length=15, choices=Signal.choices, default=Signal.HEALTHY)
    last_evaluated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "member_retention_signals"
        unique_together = [("gym", "user")]
        indexes = [
            models.Index(fields=["signal"]),
            models.Index(fields=["churn_risk_score"]),
        ]

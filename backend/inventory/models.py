from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def tool_count(self):
        return self.tools.count()


class Tool(models.Model):
    TYPE_CHOICES = [
        ('plant', 'Plant'),
        ('equipment', 'Equipment'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tools',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def location(self):
        return self.project.name if self.project else 'Warehouse'

    @property
    def status(self):
        return 'assigned' if self.project else 'warehouse'


class AllocationHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
    ]

    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name='history',
    )
    tool_name = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    from_location = models.CharField(max_length=255, blank=True, default='')
    to_location = models.CharField(max_length=255)
    performed_by = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tool_name}: {self.action} → {self.to_location}"

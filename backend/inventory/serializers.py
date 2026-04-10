from rest_framework import serializers
from .models import Tool, Project, AllocationHistory


class ProjectSerializer(serializers.ModelSerializer):
    tool_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'tool_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class ToolSerializer(serializers.ModelSerializer):
    location = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)

    class Meta:
        model = Tool
        fields = ['id', 'name', 'type', 'project', 'project_name', 'location', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class AllocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocationHistory
        fields = ['id', 'tool', 'tool_name', 'action', 'from_location', 'to_location', 'performed_by', 'created_at']
        read_only_fields = ['id', 'created_at']


class AllocateToolSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(allow_null=True)


class BulkToolSerializer(serializers.Serializer):
    """For CSV import — accepts a list of tools."""
    tools = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=False,
    )


class DashboardProjectSerializer(serializers.ModelSerializer):
    """Project with its tools nested for the dashboard view."""
    tools = ToolSerializer(many=True, read_only=True)
    tool_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'tool_count', 'tools', 'created_at']

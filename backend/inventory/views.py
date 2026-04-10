from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Tool, Project, AllocationHistory
from .serializers import (
    ToolSerializer,
    ProjectSerializer,
    AllocationHistorySerializer,
    AllocateToolSerializer,
    BulkToolSerializer,
    DashboardProjectSerializer,
)


class ToolViewSet(viewsets.ModelViewSet):
    queryset = Tool.objects.select_related('project').all()
    serializer_class = ToolSerializer

    def perform_create(self, serializer):
        tool = serializer.save()
        user_name = self._get_user_display(self.request)
        AllocationHistory.objects.create(
            tool=tool,
            tool_name=tool.name,
            action='created',
            from_location='',
            to_location='Warehouse',
            performed_by=user_name,
        )

    def perform_destroy(self, instance):
        AllocationHistory.objects.filter(tool=instance).delete()
        instance.delete()

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        tool = self.get_object()
        serializer = AllocateToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_project_id = serializer.validated_data['project_id']
        new_project = Project.objects.get(id=new_project_id) if new_project_id else None

        old_location = tool.location
        new_location = new_project.name if new_project else 'Warehouse'

        if old_location == new_location:
            return Response({'detail': 'Tool is already at this location.'}, status=status.HTTP_400_BAD_REQUEST)

        action_type = 'assigned' if new_project else 'returned'
        user_name = self._get_user_display(request)

        AllocationHistory.objects.create(
            tool=tool,
            tool_name=tool.name,
            action=action_type,
            from_location=old_location,
            to_location=new_location,
            performed_by=user_name,
        )

        tool.project = new_project
        tool.save()

        return Response(ToolSerializer(tool).data)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        serializer = BulkToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_name = self._get_user_display(request)
        created = []
        skipped = []

        for item in serializer.validated_data['tools']:
            name = item.get('name', '').strip()
            tool_type = item.get('type', 'equipment').strip().lower()

            if not name:
                continue

            if tool_type not in ('plant', 'equipment'):
                tool_type = 'equipment'

            if Tool.objects.filter(name__iexact=name).exists():
                skipped.append(name)
                continue

            tool = Tool.objects.create(name=name, type=tool_type)
            AllocationHistory.objects.create(
                tool=tool,
                tool_name=tool.name,
                action='created',
                from_location='',
                to_location='Warehouse',
                performed_by=user_name,
            )
            created.append(name)

        return Response({
            'created_count': len(created),
            'skipped_count': len(skipped),
            'created': created,
            'skipped': skipped,
        }, status=status.HTTP_201_CREATED)

    def _get_user_display(self, request):
        if request.user and request.user.is_authenticated:
            return request.user.get_full_name() or request.user.username
        return ''


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def perform_destroy(self, instance):
        # Return all tools to warehouse before deleting project
        tools = Tool.objects.filter(project=instance)
        for tool in tools:
            AllocationHistory.objects.create(
                tool=tool,
                tool_name=tool.name,
                action='returned',
                from_location=instance.name,
                to_location='Warehouse',
                performed_by='',
            )
            tool.project = None
            tool.save()
        instance.delete()


class AllocationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AllocationHistory.objects.select_related('tool').all()
    serializer_class = AllocationHistorySerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """
    Returns full dashboard data: stats + projects with nested tools.
    """
    tools = Tool.objects.select_related('project').all()
    projects = Project.objects.prefetch_related('tools').all()

    total = tools.count()
    plant_count = tools.filter(type='plant').count()
    equip_count = tools.filter(type='equipment').count()
    warehouse_count = tools.filter(project__isnull=True).count()
    assigned_count = tools.filter(project__isnull=False).count()

    # Warehouse tools (unassigned)
    warehouse_tools = ToolSerializer(tools.filter(project__isnull=True), many=True).data

    # Projects with nested tools
    project_data = DashboardProjectSerializer(projects, many=True).data

    return Response({
        'stats': {
            'total_tools': total,
            'plant_count': plant_count,
            'equipment_count': equip_count,
            'warehouse_count': warehouse_count,
            'assigned_count': assigned_count,
            'project_count': projects.count(),
        },
        'warehouse': {
            'name': 'Warehouse',
            'tools': warehouse_tools,
            'tool_count': warehouse_count,
        },
        'projects': project_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Returns the authenticated user's info."""
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.get_full_name(),
    })

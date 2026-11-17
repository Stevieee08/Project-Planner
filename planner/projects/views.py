from django.shortcuts import get_object_or_404, render

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import AssignedProjects, Project,Task

from .serializers import AssignedProjectSerializer, ProjectSerializer,TaskSerializers

from rest_framework.views import APIView

from rest_framework.response import Response

from planner.utils import generate_tasks

from django.db import transaction

from planner.paginations import CustomPagination
# Create your views here.

class ProjectListCreateView(ListCreateAPIView):

    pagination_class = CustomPagination

    queryset=Project.objects.filter(active_status=True)

    serializer_class= ProjectSerializer


class ProjectRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):

    lookup_field='uuid'

    queryset=Project.objects.filter(active_status=True)

    serializer_class= ProjectSerializer

    def perform_destroy(self,instance):
        
        instance.active_status=False

        instance.save()


class AssignedProjectListCreateView(ListCreateAPIView):

    pagination_class = CustomPagination

    queryset = AssignedProjects.objects.filter(active_status=True).select_related('project', 'coordinator').prefetch_related('developer')

    serializer_class = AssignedProjectSerializer


class AssignedProjectRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):

    lookup_field = 'uuid'

    queryset = AssignedProjects.objects.filter(active_status=True).select_related('project', 'coordinator').prefetch_related('developer')

    serializer_class = AssignedProjectSerializer

    def perform_destroy(self, instance):

        instance.active_status = False

        instance.save(update_fields=['active_status', 'updated_at'])

class TaskListCreateView(ListCreateAPIView):

    pagination_class = CustomPagination

    def get_queryset(self):

        project_uuid = self.request.query_params.get('project')

        if not project_uuid:
            return Task.objects.none()

        try:
            project_uuid = serializers.UUIDField().run_validation(project_uuid)
        except ValidationError as exc:
            raise ValidationError({'project': 'A valid UUID is required.'}) from exc

        return Task.objects.filter(
            assigned_project__uuid=project_uuid
        ).select_related('assigned_project', 'assigned_to')

    serializer_class= TaskSerializers

class TaskRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):

    lookup_field = 'uuid'

    queryset = Task.objects.filter(active_status=True).select_related('assigned_project', 'assigned_to')

    serializer_class = TaskSerializers

    def perform_destroy(self, instance):

        instance.active_status = False

        instance.save(update_fields=['active_status', 'updated_at'])

class TaskCreateWithAI(APIView):

    def post(self,*args,**kwargs):

        uuid=kwargs.get('uuid')

        try:

            assigned_project = get_object_or_404(AssignedProjects, uuid=uuid)

            result=generate_tasks(assigned_project)

            tasks = [Task(title=task.title,
                            description=task.description,
                            assigned_project=assigned_project,
                            assigned_to_id=task.developer_id,
                            priority=task.priority) for task in result.tasks]

            with transaction.atomic():

                Task.objects.bulk_create(tasks)

                data={'msg':'Tasks assigned successfully.'}

                return Response(data,status=200)

        except Exception as e :

                print(e)

                data={'msg':'failed to create tasks'}

                return Response(data,status=400)

    

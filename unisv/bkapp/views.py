from rest_framework import generics, status
from rest_framework.response import Response
from .models import Todo, Tag
from .serializers import TodoSerializer

class ListCreateTodo(generics.ListCreateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

class DetailUpdateTodo(generics.RetrieveUpdateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        # 在这里可以添加更多的业务逻辑
        todo = serializer.save()
        # 例如，你可以在这里处理其他表的更新
        # 假设你有一个相关的 Tag 表
        tag_ids = self.request.data.get('tag_ids', [])
        todo.tags.set(tag_ids)
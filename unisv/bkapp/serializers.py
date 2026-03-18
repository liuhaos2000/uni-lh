from rest_framework import serializers
from .models import Todo, Tag

class TodoSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Todo
        fields = ('id', 'title', 'body',)

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

def update(self, instance, validated_data):
    # 更新 Todo 对象
    instance.title = validated_data.get('title', instance.title)
    instance.description = validated_data.get('description', instance.description)
    instance.completed = validated_data.get('completed', instance.completed)
    instance.save()

    # 更新或添加标签
    tag_ids = validated_data.pop('tags', [])
    instance.tags.set(tag_ids)

    return instance
from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def test_api(request):
    if request.method == 'GET':
        return Response({"message": "GET 요청 성공!"})
    
    elif request.method == 'POST':
        data = request.data  # POST된 데이터
        return Response({"message": "POST 요청 성공!", "data": data})

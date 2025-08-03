from django.urls import path
from . import views

app_name = 'storage'

urlpatterns = [
    # Datasets
    path('datasets/', views.DatasetListView.as_view(), name='dataset-list'),
    path('datasets/<int:dataset_id>/', views.DatasetDetailView.as_view(), name='dataset-detail'),
    
    # Shares
    path('shares/', views.ShareListView.as_view(), name='share-list'),
    path('shares/<int:share_id>/', views.ShareDetailView.as_view(), name='share-detail'),
    
    # Share ACLs
    path('shares/<int:share_id>/acls/', views.ShareACLView.as_view(), name='share-acls'),
    
    # Users
    path('users/', views.UserAccountListView.as_view(), name='user-list'),
]
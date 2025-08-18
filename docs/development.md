# MoxNAS Development Guide

This guide covers setting up a development environment for contributing to MoxNAS.

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Node.js 16+
- Git
- Docker (optional, for containerized development)

### Clone Repository

```bash
git clone https://github.com/moxnas/moxnas.git
cd moxnas
```

### Backend Development

#### Virtual Environment Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

#### Database Setup

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

#### Run Development Server

```bash
python manage.py runserver 0.0.0.0:8001
```

### Frontend Development

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Run Development Server

```bash
npm start
```

The frontend will be available at `http://localhost:3000` and will proxy API requests to the backend.

### Full Stack Development

Use Docker Compose for full stack development:

```bash
# In project root
docker-compose -f docker-compose.dev.yml up
```

This starts:
- Backend API server
- Frontend development server
- PostgreSQL database
- Redis cache

## Project Structure

```
MoxNAS/
├── backend/                 # Django backend
│   ├── moxnas/             # Main project
│   ├── apps/               # Django applications
│   ├── static/             # Static files
│   └── templates/          # Django templates
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── styles/         # CSS styles
│   └── public/             # Public assets
├── services/               # NAS service configs
├── scripts/                # Utility scripts
├── config/                 # Configuration files
├── docs/                   # Documentation
└── tests/                  # Test suites
```

## Development Workflow

### Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "Add feature"`
3. Push branch: `git push origin feature/your-feature`
4. Create pull request
5. Code review and merge

### Code Standards

#### Python (Backend)

- Follow PEP 8 style guide
- Use Black for code formatting
- Use isort for import sorting
- Type hints recommended

```bash
# Format code
black .
isort .

# Lint code
flake8 .
pylint apps/
```

#### JavaScript (Frontend)

- Use ESLint and Prettier
- Follow React best practices
- Use TypeScript for new components

```bash
# Format code
npm run format

# Lint code
npm run lint
```

### Testing

#### Backend Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.storage

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

#### Frontend Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage
```

#### Integration Tests

```bash
# Run integration test suite
pytest tests/integration/
```

## Adding New Features

### Backend Feature Development

1. **Create Django App**
   ```bash
   python manage.py startapp myfeature
   ```

2. **Add Models**
   ```python
   # apps/myfeature/models.py
   from django.db import models
   
   class MyModel(models.Model):
       name = models.CharField(max_length=100)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

3. **Create Serializers**
   ```python
   # apps/myfeature/serializers.py
   from rest_framework import serializers
   from .models import MyModel
   
   class MyModelSerializer(serializers.ModelSerializer):
       class Meta:
           model = MyModel
           fields = '__all__'
   ```

4. **Add Views**
   ```python
   # apps/myfeature/views.py
   from rest_framework import viewsets
   from .models import MyModel
   from .serializers import MyModelSerializer
   
   class MyModelViewSet(viewsets.ModelViewSet):
       queryset = MyModel.objects.all()
       serializer_class = MyModelSerializer
   ```

5. **Configure URLs**
   ```python
   # apps/myfeature/urls.py
   from rest_framework.routers import DefaultRouter
   from .views import MyModelViewSet
   
   router = DefaultRouter()
   router.register(r'mymodel', MyModelViewSet)
   urlpatterns = router.urls
   ```

6. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### Frontend Feature Development

1. **Create Component**
   ```jsx
   // src/components/MyComponent.jsx
   import React from 'react';
   
   const MyComponent = () => {
     return (
       <div>
         <h1>My Feature</h1>
       </div>
     );
   };
   
   export default MyComponent;
   ```

2. **Add API Service**
   ```javascript
   // src/services/myfeature.js
   import api from './api';
   
   export const myFeatureService = {
     getAll: () => api.get('/myfeature/'),
     create: (data) => api.post('/myfeature/', data),
     update: (id, data) => api.put(`/myfeature/${id}/`, data),
     delete: (id) => api.delete(`/myfeature/${id}/`)
   };
   ```

3. **Add Route**
   ```jsx
   // src/App.jsx
   import MyComponent from './components/MyComponent';
   
   // Add to routes
   <Route path="/myfeature" element={<MyComponent />} />
   ```

## Service Integration

### Adding NAS Services

1. **Create Service Directory**
   ```bash
   mkdir services/myservice
   ```

2. **Add Configuration Template**
   ```bash
   # services/myservice/myservice.conf.template
   [global]
   setting1 = {{ setting1 }}
   setting2 = {{ setting2 }}
   ```

3. **Create Service Manager**
   ```python
   # services/myservice/myservice-config.py
   class MyServiceConfig:
       def __init__(self):
           self.template = self._load_template()
       
       def generate_config(self, data):
           return self.template.render(**data)
   ```

4. **Add Django Integration**
   ```python
   # apps/services/managers.py
   from services.myservice.myservice-config import MyServiceConfig
   
   class MyServiceManager:
       def __init__(self):
           self.config = MyServiceConfig()
   ```

### System Scripts

Add utility scripts in the `scripts/` directory:

```python
#!/usr/bin/env python3
"""
My utility script for MoxNAS
"""

import sys
import logging

def main():
    # Script logic here
    pass

if __name__ == '__main__':
    main()
```

## Documentation

### Adding Documentation

1. Create markdown files in `docs/`
2. Update navigation in main documentation
3. Include code examples
4. Add API documentation for new endpoints

### API Documentation

API documentation is auto-generated from Django REST Framework. Add docstrings to views:

```python
class MyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing my resources.
    
    list:
    Return a list of all resources.
    
    create:
    Create a new resource.
    """
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
```

## Debugging

### Backend Debugging

1. **Django Debug Toolbar**
   ```python
   # settings.py
   INSTALLED_APPS += ['debug_toolbar']
   MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
   ```

2. **Logging**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.debug('Debug message')
   ```

3. **Django Shell**
   ```bash
   python manage.py shell
   ```

### Frontend Debugging

1. **React Developer Tools**
   - Install browser extension
   - Inspect component hierarchy and props

2. **Console Debugging**
   ```javascript
   console.log('Debug data:', data);
   console.table(arrayData);
   ```

3. **Network Tab**
   - Monitor API requests
   - Check response status and data

## Performance Optimization

### Backend Optimization

1. **Database Queries**
   ```python
   # Use select_related for foreign keys
   queryset = MyModel.objects.select_related('foreign_key')
   
   # Use prefetch_related for many-to-many
   queryset = MyModel.objects.prefetch_related('many_to_many')
   ```

2. **Caching**
   ```python
   from django.core.cache import cache
   
   result = cache.get('my_key')
   if result is None:
       result = expensive_operation()
       cache.set('my_key', result, timeout=300)
   ```

3. **Database Indexing**
   ```python
   class MyModel(models.Model):
       name = models.CharField(max_length=100, db_index=True)
   ```

### Frontend Optimization

1. **Code Splitting**
   ```javascript
   const LazyComponent = React.lazy(() => import('./LazyComponent'));
   ```

2. **Memoization**
   ```javascript
   const MemoizedComponent = React.memo(MyComponent);
   ```

3. **State Management**
   ```javascript
   // Use React Context for global state
   const [state, setState] = useState(initialState);
   ```

## Release Process

### Version Management

1. Update version numbers
2. Update CHANGELOG.md
3. Create release tag
4. Build and test packages

### Deployment

1. **Production Build**
   ```bash
   # Frontend
   npm run build
   
   # Backend
   python manage.py collectstatic --noinput
   ```

2. **Docker Images**
   ```bash
   docker build -t moxnas:latest .
   docker push moxnas:latest
   ```

3. **Release Notes**
   - Document new features
   - List bug fixes
   - Include upgrade instructions

## Contributing Guidelines

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Update documentation
5. Submit pull request
6. Address review feedback

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Performance impact considered
- [ ] Security implications reviewed

### Issue Reporting

When reporting issues:

1. Use issue templates
2. Provide reproduction steps
3. Include system information
4. Add relevant logs
5. Suggest potential solutions

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Material-UI Documentation](https://mui.com/)
- [ZFS Documentation](https://openzfs.github.io/openzfs-docs/)
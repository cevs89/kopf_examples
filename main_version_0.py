import kopf
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.client import V1DeleteOptions

# Configurar la conexión con el clúster Kubernetes
config.load_kube_config()

# Clase para definir un recurso de Kubernetes
class KubernetesResource:
    def __init__(self, api_version, kind, metadata, spec, namespace=None):  # Añadir el campo namespace con valor predeterminado None
        self.api_version = api_version
        self.kind = kind
        self.metadata = metadata
        self.spec = spec
        self.namespace = namespace  # Almacenar el valor del namespace


mysql_resource = KubernetesResource(
    api_version="apps/v1",
    kind="Deployment",
    metadata={"name": "mysql"},
    spec={
        "replicas": 1,
        "selector": {"matchLabels": {"app": "mysql"}},
        "template": {
            "metadata": {"labels": {"app": "mysql"}},
            "spec": {
                "containers": [
                    {
                        "name": "mysql",
                        "image": "mysql:latest",
                        "ports": [{"containerPort": 3306}],
                        "env": [{"name": "MYSQL_ROOT_PASSWORD", "value": "password"}],
                    }
                ]
            },
        },
    },
)


@kopf.on.create('apps/v1', 'Deployment', labels={'app': 'mysql'})
def create_mysql(spec, **kwargs):
    deployment_name = 'mysql'

    try:
        api_instance = client.AppsV1Api()
        api_instance.delete_namespaced_deployment(
            name=deployment_name,
            namespace='default',
            body=V1DeleteOptions(grace_period_seconds=0)
        )
        print("Despliegue existente de MySQL eliminado correctamente.")
    except ApiException as e:
        if e.status != 404:
            print("Error al eliminar el despliegue existente de MySQL:", e)
            raise

    try:
        deployment_body = {
            "apiVersion": mysql_resource.api_version,
            "kind": mysql_resource.kind,
            "metadata": mysql_resource.metadata,
            "spec": mysql_resource.spec
        }
        client.AppsV1Api().create_namespaced_deployment(namespace='default', body=deployment_body)
        print("Despliegue de MySQL creado correctamente.")
    except ApiException as e:
        print("Error al crear el despliegue de MySQL:", e)
        raise


# Definir los recursos de WordPress y MySQL como objetos Python
wordpress_resource = KubernetesResource(
    api_version="apps/v1",
    kind="Deployment",
    metadata={"name": "wordpress"},
    spec={
        "replicas": 1,
        "selector": {"matchLabels": {"app": "wordpress"}},
        "template": {
            "metadata": {"labels": {"app": "wordpress"}},
            "spec": {
                "containers": [
                    {
                        "name": "wordpress",
                        "image": "wordpress:latest",
                        "ports": [{"containerPort": 80}],
                        "env": [
                            {"name": "WORDPRESS_DB_HOST", "value": "mysql"},
                            {"name": "WORDPRESS_DB_PASSWORD", "value": "password"},
                        ],
                    }
                ]
            },
        },
    },
)


@kopf.on.create('example.com', 'v1', 'wordpress')
def create_wordpress(body, spec, **kwargs):
    deployment_name = 'wordpress'
    api_core = client.CoreV1Api()
    _namespace = "wordpress-namespace"
    
    api_core.create_namespace(body=client.V1Namespace(metadata=dict(name=_namespace)))

    try:
        api_instance = client.AppsV1Api()
        api_instance.delete_namespaced_deployment(
            name=deployment_name,
            namespace=_namespace,
            body=V1DeleteOptions(grace_period_seconds=0)
        )
        print("Despliegue existente eliminado correctamente.")
    except ApiException as e:
        if e.status != 404:
            print("Error al eliminar el despliegue existente:", e)
            raise

    try:
        deployment_body = {
            "apiVersion": wordpress_resource.api_version,
            "kind": wordpress_resource.kind,
            "metadata": wordpress_resource.metadata,
            "spec": wordpress_resource.spec
        }
        client.AppsV1Api().create_namespaced_deployment(namespace=_namespace, body=deployment_body)
        print("Despliegue de WordPress creado correctamente.")
    except ApiException as e:
        print("Error al crear el despliegue de WordPress:", e)
        raise



if __name__ == '__main__':
    kopf.run()

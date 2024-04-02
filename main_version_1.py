import kopf
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.client import V1DeleteOptions

config.load_kube_config()

class KubernetesResource:
    def __init__(self, api_version, kind, metadata, spec, namespace=None):  # Añadir el campo namespace con valor predeterminado None
        self.api_version = api_version
        self.kind = kind
        self.metadata = metadata
        self.spec = spec
        self.namespace = namespace


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

wordpress_service_resource = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": "wordpress-external",
        "namespace": "wordpress-namespace",
        "labels": {
            "app": "wordpress"
        }
    },
    "spec": {
        "type": "LoadBalancer",
        "selector": {
            "app": "wordpress"
        },
        "ports": [
            {
                "name": "http",
                "protocol": "TCP",
                "port": 80,
                "targetPort": 80,
                "nodePort": 30000
            }
        ]
    }
}


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

mysql_service_resource = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": "mysql-service",
        "namespace":  "wordpress-namespace",
        "labels": {
            "app": "wordpress"
        }
    },
    "spec": {
        "selector": {
            "app": "wordpress"
        },
        "ports": [
            {
                "name": "mysql",
                "protocol": "TCP",
                "port": 3066,
                "targetPort": 3066
            }
        ],
        "clusterIP": "None"
    }
}


@kopf.on.create('example.com', 'v1', 'wordpress')
def create_wordpress(spec, **kwargs):
    deployment_name = 'wordpress'

    _namespace = "wordpress-namespace"
    client.CoreV1Api().create_namespace(body=client.V1Namespace(metadata=dict(name=_namespace)))

    # Borrar  deployments
    try:
        client.AppsV1Api().delete_namespaced_deployment(
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
            "apiVersion": mysql_resource.api_version,
            "kind": mysql_resource.kind,
            "metadata": mysql_resource.metadata,
            "spec": mysql_resource.spec
        }
        client.AppsV1Api().create_namespaced_deployment(namespace=_namespace, body=deployment_body)
        print("Despliegue de MySQL creado correctamente.")
    except ApiException as e:
        print("Error al crear el despliegue de MySQL:", e)
        raise



    # Create the service from the substituted template
    try:
        client.CoreV1Api().create_namespaced_service(body=mysql_service_resource, namespace=_namespace)
        print("Service 'mysql-service' created successfully.")
    except client.ApiException as e:
        print(f"Failed to create the service. Error: {e}")
        raise

    """
    ======================================================================
    ============================= Wordpress ==============================
    ======================================================================
    """

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


    try:
        client.CoreV1Api().create_namespaced_service(body=wordpress_service_resource, namespace=_namespace)
        print("Service 'wordpress-service' created successfully.")
    except client.ApiException as e:
        print(f"Failed to create the service. Error: {e}")



if __name__ == '__main__':
    kopf.run()

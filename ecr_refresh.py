import boto3
import base64
import json
import subprocess
import os

ecr = boto3.client(
    'ecr',
    region_name=os.environ['AWS_DEFAULT_REGION'],
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
)

token = ecr.get_authorization_token()['authorizationData'][0]['authorizationToken']
# token is already base64(AWS:password) — use directly as auth field

password = base64.b64decode(token).decode().split(':', 1)[1]

registry = os.environ['ECR_REGISTRY']
namespaces = os.environ.get('NAMESPACES', 'kube-system').split()

dockerconfig = json.dumps({
    "auths": {
        registry: {
            #"auth": token

            "username": "AWS",
            "password": password
        }
    }
}, separators=(',', ':'))

for ns in namespaces:
    print(f"Updating ecr-secret in namespace: {ns}")
    with open('/tmp/dockerconfig.json', 'w', encoding='utf-8') as f:
        f.write(dockerconfig)

    result = subprocess.run([
        'kubectl', 'create', 'secret', 'generic', 'ecr-secret',
        '--from-file=.dockerconfigjson=/tmp/dockerconfig.json',
        '--type=kubernetes.io/dockerconfigjson',
        f'--namespace={ns}',
        '--dry-run=client', '-o', 'yaml'
    ], capture_output=True, text=True)

    apply = subprocess.run(
        ['kubectl', 'replace', '-f', '-', f'--namespace={ns}'],
        input=result.stdout,
        capture_output=True, text=True
    )

    if apply.returncode != 0:
        subprocess.run([
            'kubectl', 'create', 'secret', 'generic', 'ecr-secret',
            '--from-file=.dockerconfigjson=/tmp/dockerconfig.json',
            '--type=kubernetes.io/dockerconfigjson',
            f'--namespace={ns}',
        ])

    print(f"Done: {ns}")

print("All namespaces updated.")

# Skill: deploy

Build, push Docker image to ECR, and redeploy the ECS service.

## Usage

```
deploy
deploy --build-only
deploy --push-only
deploy --redeploy-only
```

## Behavior

**`deploy`** (full cycle)
```bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 959317755669.dkr.ecr.us-west-2.amazonaws.com
docker build -t ai4good/terra-backend .
docker tag ai4good/terra-backend:latest 959317755669.dkr.ecr.us-west-2.amazonaws.com/ai4good/terra-backend:latest
docker push 959317755669.dkr.ecr.us-west-2.amazonaws.com/ai4good/terra-backend:latest
aws ecs update-service --cluster default --service terra-backend-28b2 --force-new-deployment
```

**`deploy --build-only`** — only runs the docker build step

**`deploy --push-only`** — assumes image already tagged, just pushes + redeploys

**`deploy --redeploy-only`** — force-redeploys without building (picks up latest image in ECR)

## Post-deploy check

After triggering the deployment, poll until rollout completes:
```bash
aws ecs describe-services --cluster default --services terra-backend-28b2 \
  --query 'services[0].deployments[0].rolloutState'
```
Report COMPLETED or FAILED with the reason.

## Context

- ECR registry: `959317755669.dkr.ecr.us-west-2.amazonaws.com/ai4good/terra-backend`
- ECS cluster: `default`, service: `terra-backend-28b2`, region: `us-west-2`
- Container listens on port 80 (`PORT=80` env var)
- `OPENAI_API_KEY` comes from Secrets Manager — no need to pass it at build time

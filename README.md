Get a list of IBM Cloud services.

- `/`: all services offered
- `/ibm`: all services offered by IBM

Required environment variables:

```bash
export GLOBAL_CATALOG_URL=<SERVICE_URL>
export GLOBAL_CATALOG_AUTHTYPE=iam
export GLOBAL_CATALOG_APIKEY=<API_KEY>
```

Local dev env with: `uvicorn main:app --reload`

Built image: `quay.io/congxdev/ibmcloud-services-api:latest`.
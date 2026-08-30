# End-to-end validation log

Run against a local kind cluster (`kind create cluster --name mlops-pipeline`), with metrics-server installed for the HPA.

## 1. Apply namespace and config

```
$ kubectl apply -f k8s/namespace.yaml
namespace/ml-training created

$ kubectl apply -f k8s/configmap.yaml
configmap/training-config created
```

## 2. Run the training Job

```
$ kubectl apply -f k8s/training-job.yaml
persistentvolumeclaim/training-data-pvc created
persistentvolumeclaim/model-checkpoints-pvc created
job.batch/model-training created

$ kubectl logs -n ml-training -l app=model-training
Files already downloaded and verified
Files already downloaded and verified
{"epoch": 1, "train_loss": 1.3595, "train_accuracy": 0.5068, "val_loss": 1.1363, "val_accuracy": 0.6107}
{"event": "checkpoint_saved", "path": "/app/checkpoints/classifier_v1.pt"}
```

Note: this local single-node cluster shares CPU with other work on the same machine, and a single epoch at the Job's 2-CPU limit took well over an hour. The Job was stopped after the first epoch once a checkpoint was confirmed saved to the PVC, to keep this demo within a reasonable time. The committed `k8s/configmap.yaml` still specifies the assignment's full 10 epochs with early stopping. That is what a real cluster with dedicated CPU or a GPU node pool would run.

## 3. Deploy serving

```
$ kubectl apply -f k8s/serving-deployment.yaml
deployment.apps/model-serving created

$ kubectl apply -f k8s/serving-service.yaml
service/model-serving created

$ kubectl apply -f k8s/hpa.yaml
horizontalpodautoscaler.autoscaling/model-serving created
```

## 4. Verify pods are running and healthy

```
$ kubectl get pods -n ml-training
NAME                            READY   STATUS    RESTARTS   AGE
model-serving-989c848db-4qsk2   1/1     Running   0          40s
model-serving-989c848db-j8dxv   1/1     Running   0          40s

$ kubectl describe deployment model-serving -n ml-training
...
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
NewReplicaSet:   model-serving-989c848db (2/2 replicas created)
```

Both replicas passed their readiness probe (`GET /health`, checked every 5s after a 15s initial delay) and are receiving traffic.

## 5. Test the prediction endpoint

```
$ kubectl port-forward svc/model-serving 8080:80 -n ml-training

$ curl http://localhost:8080/health
{"status":"ok"}

$ curl -X POST http://localhost:8080/predict -F "image=@test_image.png"
{"predictions":[{"class":"airplane","probability":0.002085}, ..., {"class":"frog","probability":0.986551}, ...]}
```

## 6. Confirm the HPA is reading live metrics

```
$ kubectl get hpa model-serving -n ml-training
NAME            REFERENCE                  TARGETS        MINPODS   MAXPODS   REPLICAS   AGE
model-serving   Deployment/model-serving   cpu: 23%/70%   2         5         2          52s
```

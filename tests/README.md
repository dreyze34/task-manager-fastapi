# Tests

Depuis la racine du projet :

```bash
.venv/bin/python -m unittest discover -s tests -v
```

La suite utilise `unittest` (bibliothèque standard) et `httpx` pour les
requêtes HTTP ASGI. Si nécessaire, installer la dépendance HTTP avec :

```bash
.venv/bin/python -m pip install -r requirements-test.txt
```

Les dépendances de l'application doivent aussi être installées dans cet
environnement (FastAPI, Pydantic, redis-py).

Les tests ne nécessitent ni Redis ni Uvicorn en cours d'exécution et ne
modifient aucune donnée Redis. Les tests HTTP utilisent la vraie application,
ses routes et ses services, avec un repository et une queue en mémoire. Le
lifespan de production n'est pas exécuté ; la connexion et le démarrage Redis
ne sont donc pas validés par ces tests. Les adaptateurs Redis sont testés avec
un client simulé, pas avec un serveur Redis réel.

Les tests du worker vérifient notamment que l'état final est enregistré avant
la confirmation du message et qu'une panne de stockage empêche sa confirmation,
conformément à ARCHITECTURE.md.

Trois tests sont marqués `expectedFailure` pour rendre visibles les écarts
actuels avec ARCHITECTURE.md sans modifier le code de l'application :

- le POST /jobs retourne 200 au lieu de 202 ;
- les types de jobs inconnus ne sont pas rejetés ;
- les payloads métier invalides ne sont pas rejetés.

Les tests de validation attendent une ValueError (ou une sous-classe) : adapter
ce contrat si une exception métier dédiée est introduite. Lors de la correction
de chaque écart, retirer son décorateur `expectedFailure`. Un succès inattendu
fait échouer la suite afin de rappeler cette mise à jour.

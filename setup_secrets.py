import getpass
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

weather_url = getpass.getpass(
    "Paste Weather Lakebase connection URL: "
)

w.secrets.put_secret(
    scope="database",
    key="weather-lakebase-url",
    string_value=weather_url,
)

print("Weather Lakebase secret stored.")

for secret in w.secrets.list_secrets(scope="database"):
    print(secret.key)


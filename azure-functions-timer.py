import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import ContainerExecRequest
import json
import os

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function that runs the OSAA MVP ETL pipeline on a schedule.
    This replaces the GitHub Actions daily_transform.yml workflow.
    """
    utc_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')
    
    logging.info('Starting OSAA MVP ETL pipeline execution at %s', utc_timestamp)
    
    try:
        # Azure configuration
        subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
        resource_group_name = os.environ.get('AZURE_RESOURCE_GROUP', 'osaa-mvp-rg')
        container_group_name = os.environ.get('AZURE_CONTAINER_NAME', 'osaa-mvp')
        
        # Initialize Azure client
        credential = DefaultAzureCredential()
        container_client = ContainerInstanceManagementClient(credential, subscription_id)
        
        # Execute ETL pipeline
        exec_request = ContainerExecRequest(
            command="/app/entrypoint.sh etl",
            terminal_size={
                "rows": 80,
                "cols": 120
            }
        )
        
        # Run the ETL command
        response = container_client.containers.execute_command(
            resource_group_name=resource_group_name,
            container_group_name=container_group_name,
            container_name=container_group_name,
            container_exec_request=exec_request
        )
        
        logging.info('ETL pipeline execution completed successfully')
        logging.info('Response: %s', response)
        
        # Optional: Send notification
        send_notification("ETL pipeline completed successfully", "success")
        
    except Exception as e:
        logging.error('ETL pipeline execution failed: %s', str(e))
        send_notification(f"ETL pipeline failed: {str(e)}", "error")
        raise

def send_notification(message: str, status: str):
    """Send notification about pipeline status (optional)"""
    try:
        # You can integrate with various notification services:
        # - Slack webhook
        # - Teams webhook  
        # - Email via SendGrid
        # - Azure Service Bus
        logging.info(f"Notification: {message} - Status: {status}")
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")

# Azure Function configuration
# host.json:
# {
#   "version": "2.0",
#   "functionTimeout": "00:10:00",
#   "extensions": {
#     "http": {
#       "routePrefix": "api"
#     }
#   }
# }

# function.json:
# {
#   "scriptFile": "azure-functions-timer.py",
#   "bindings": [
#     {
#       "name": "mytimer",
#       "type": "timerTrigger",
#       "direction": "in",
#       "schedule": "0 0 6 * * *"
#     }
#   ]
# }

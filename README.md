# AWS AI Manager

## Project Description

The AWS AI Manager is a Streamlit-based conversational AI application designed to simplify the management of AWS cloud resources. It allows users to interact with their AWS environment using natural language commands, leveraging Terraform for infrastructure provisioning and a large language model (LLM) for intelligent responses and assistance.

## Features

*   **Conversational Interface**: Manage AWS resources through a user-friendly chat interface with robust natural language understanding.
*   **Enhanced Resource Management**: Create, destroy, list, and modify various AWS resources, including:
    *   EC2 Instances (with root and data volumes, and now correctly handles private IPs)
    *   S3 Buckets
    *   RDS Databases (now supports public/private accessibility configuration)
    *   DynamoDB Tables
    *   IAM Users, Roles, and Policies (all resource types now have comprehensive parameter modification support)
*   **AI-Powered Assistance**:
    *   **Intelligent Intent Recognition**: AI understands context and translates requests into AWS actions.
    *   **Automated Terraform Provisioning**: Seamlessly generates and applies Infrastructure as Code (IaC) for consistent deployments.
    *   **Cost Estimation**: Get estimated costs for your AWS resource requests.
    *   **Error Diagnosis**: Receive AI-driven insights and suggestions for resolving AWS-related errors.
    *   **Improved Error Handling & Retry**: Robust error handling with the ability to modify parameters and retry failed resource creation attempts.
*   **Session Persistence**: Your conversation history and application state are saved, allowing you to resume where you left off even if the application restarts.
*   **Detailed Progress Indicators**: Provides real-time updates during long-running Terraform operations.
*   **Resource Modification**: Supports modifying parameters of existing resources (e.g., EC2 instance volume size).

## Security Considerations

**WARNING: Insecure RDS Security Group Configuration**

The current Terraform configuration for RDS instances (`terraformfile/rds/maincode/net.tf`) creates a security group that allows **all inbound TCP traffic from `0.0.0.0/0` (any IP address) on all ports**. This is highly insecure and **NOT recommended for production environments**. It is intended for demonstration or testing purposes only.

**Before deploying to a production environment, you MUST modify the `ingress` rules in `terraformfile/rds/maincode/net.tf` to restrict inbound traffic to known IP addresses and specific ports.**

## Setup and Usage

### Prerequisites

*   **Python 3.x**: Ensure Python is installed on your system.
*   **AWS CLI Configured**: You need to have the AWS Command Line Interface (CLI) installed and configured with appropriate credentials and a default region. The application will use these credentials to interact with your AWS account.
*   **Terraform Installed**: Terraform must be installed and accessible in your system's PATH.

### Installation

1.  **Navigate to the project directory**:
    ```bash
    cd C:\Users\desai\gemini-cli\AWS_AI_MANAGER
    ```
2.  **Create a Python virtual environment (recommended)**:
    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment**:
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
4.  **Install required Python packages**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Configure Perplexity AI API Key**:
    The application uses the Perplexity AI API for its intelligent responses. Create a file named `.env` in the root of the `AWS_AI_MANAGER` directory and add your Perplexity AI API key:
    ```
    PERPLEXITY_API_KEY="your_perplexity_api_key_here"
    ```

### Running the Application

1.  **Activate your virtual environment** (if not already active).
2.  **Run the Streamlit application**:
    ```bash
    streamlit run streamlit_app.py
    ```
    This will open the application in your web browser.

### Interacting with the AI

Type your AWS resource management requests into the chat input. Examples:

*   "Create an EC2 instance"
*   "Destroy my S3 bucket named my-test-bucket"
*   "List all running EC2 instances"
*   "Estimate the cost of a t3.micro EC2 instance with 50GB storage"
*   "Modify EC2 instance i-0abcdef1234567890 root volume size to 100GB"
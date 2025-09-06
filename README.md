# 🗣️ Talk to Your Cloud: Your AI Co-Pilot for AWS

### *Stop clicking, stop scripting, start talking. A journey into building a conversational AI that manages AWS for you.*

---

**AWS AI Manager** is a proof-of-concept that reimagines cloud infrastructure management. Instead of navigating the complex AWS Console or memorizing CLI commands, this tool allows you to manage your AWS resources through a simple, intuitive, and conversational chat interface.

It's your personal AI co-pilot, designed to understand what you want to do and translate your plain English requests into production-ready Infrastructure as Code.

<br>

## ✨ Key Features

*   **💬 Natural Language Management:** Describe the resources you need in plain English. The AI handles the rest.
*   **🧠 Intelligent & Inquisitive:** The AI asks for missing information, provides smart suggestions, and confirms actions before executing.
*   **🏗️ Automated Terraform Generation:** Converts conversations into reliable and repeatable Terraform code that gets applied automatically.
*   **☁️ Multi-Service AWS Support:** Natively manages key AWS services:
    *   **EC2** (Virtual Machines)
    *   **RDS** (Relational Databases)
    *   **S3** (Object Storage)
    *   **DynamoDB** (NoSQL Databases)
    *   **IAM** (Users, Roles, & Policies)
*   **💰 Built-in Cost Estimation:** Ask "How much will this cost?" before you deploy.
*   **🛠️ Smart Error Recovery:** If something goes wrong, the AI analyzes the error and suggests a fix.
*   **💾 Session Persistence:** Close the browser and pick up your conversation right where you left off.

<br>

## 🏛️ How It Works: The Architecture

The application uses a modular Python backend that orchestrates the conversation, AI logic, and infrastructure automation.

```
AWS AI Manager/
├── streamlit_app.py          # Main Streamlit application UI
├── utils/
│   ├── intent_classifier.py   # Figures out what you want to do
│   ├── parameter_extractor.py # Pulls out the key details (e.g., instance type)
│   ├── conversation_handler.py# Manages the back-and-forth chat flow
│   └── ai_client.py           # Connects to the Large Language Model
├── services/
│   └── terraform_service.py   # Interacts with Terraform to apply changes
└── terraformfile/
    ├── ec2/                   # Pre-defined Terraform templates for EC2
    └── rds/                   # ...and for RDS, S3, etc.
```

<br>

## 🚀 Quick Start

### Prerequisites

*   Python 3.8+
*   AWS CLI configured with your credentials (`aws configure`)
*   Terraform 1.0+ installed
*   A Perplexity AI API Key

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd AWS_AI_MANAGER
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your API Key:** Create a file named `.env` in the project root and add your key:
    ```
    PERPLEXITY_API_KEY="your_api_key_here"
    ```

5.  **Run the application:**
    ```bash
    streamlit run streamlit_app.py
    ```
The application will open in your web browser.

<br>

## 💬 Usage Examples

#### **Create an EC2 Instance**

> **You:** "create an ec2 instance"
>
> **System:** "Of course. What would you like to name it? I can also suggest an AMI and instance type if you're unsure."

#### **Create a Production Database**

> **You:** "I need a production postgres 14 database with 200GB of storage"
>
> **System:** "Understood. I'm setting up a production-grade PostgreSQL 14 instance. I'll ask for a few more details before we proceed."

#### **Create an S3 Bucket**

> **You:** "create a bucket for my website's assets"
>
> **System:** "Sounds good. I'll suggest a globally unique name and some standard configuration options for a website asset bucket."

<br>

## 🔒 Security Considerations

*   **API Keys:** Your Perplexity API key is stored locally in the `.env` file and should never be committed to version control.
*   **AWS Credentials:** The tool uses the credentials configured in your local AWS CLI profile. It's highly recommended to use an IAM user with the minimum required permissions.
*   **RDS Security Groups:** The default RDS configuration may allow broad inbound access for demonstration purposes. **Never use this in production without locking down the security groups.**

<br>

## 🤝 Contributing

This is a proof-of-concept and a great starting point for a more robust tool. Contributions are welcome!

1.  **Fork the repository.**
2.  Create a new feature branch (`git checkout -b feature/your-idea`).
3.  Make your changes and commit them (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/your-idea`).
5.  Open a Pull Request.

<br>

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
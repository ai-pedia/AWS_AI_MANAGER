# AWS AI Manager

## 🚀 Project Overview

AWS AI Manager is an advanced conversational AI application that revolutionizes AWS cloud resource management through natural language processing. Built with Streamlit and powered by cutting-edge AI, it enables users to manage their AWS infrastructure using intuitive, human-like conversations.

## ✨ Key Features

### 🤖 Intelligent Conversation Flow
- **Natural Language Processing**: Understands complex AWS requests in plain English
- **Context-Aware Responses**: Maintains conversation context across interactions
- **Smart Parameter Extraction**: Automatically identifies and extracts AWS resource parameters
- **Progressive Parameter Collection**: Guides users through required parameters with intelligent suggestions

### 🏗️ Comprehensive AWS Resource Management
- **EC2 Instances**: Create, modify, and manage EC2 instances with full configuration support
- **RDS Databases**: Deploy and configure relational databases (PostgreSQL, MySQL, Aurora)
- **S3 Buckets**: Manage object storage with advanced configuration options
- **DynamoDB Tables**: Create and manage NoSQL databases with flexible schemas
- **IAM Resources**: Handle users, roles, and policies for access management

### 🔧 Advanced Capabilities
- **Automated Terraform Generation**: Converts natural language into Infrastructure as Code
- **Cost Estimation**: Real-time cost calculations for resource deployments
- **Error Recovery**: Intelligent error diagnosis and resolution suggestions
- **Session Persistence**: Resume conversations and maintain state across sessions
- **Batch Operations**: Handle multiple resource requests in a single conversation

## 🏛️ Architecture

### Core Components

```
AWS AI Manager/
├── streamlit_app.py          # Main Streamlit application
├── utils/
│   ├── parameter_extractor.py # Advanced parameter extraction with AI
│   ├── intent_classifier.py   # Intent recognition and classification
│   ├── conversation_handler.py# Conversation flow management
│   ├── context_manager.py     # Session and user context management
│   ├── suggestion_engine.py   # Intelligent parameter suggestions
│   ├── error_recovery.py      # Error handling and recovery
│   └── ai_client.py          # Perplexity AI integration
├── services/
│   └── aws_service.py         # AWS API interactions
├── terraformfile/
│   ├── ec2/                   # EC2 Terraform templates
│   ├── rds/                   # RDS Terraform templates
│   ├── s3/                    # S3 Terraform templates
│   └── dynamodb/              # DynamoDB Terraform templates
└── requirements.txt           # Python dependencies
```

### Parameter Extraction System

The enhanced parameter extraction system features:
- **No Automatic Defaults**: Users are always asked for required parameters
- **Intelligent Suggestions**: Context-aware parameter value suggestions
- **User History Integration**: Personalized suggestions based on usage patterns
- **Validation & Error Handling**: Robust parameter validation with helpful error messages

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **AWS CLI** configured with appropriate credentials
- **Terraform 1.0+**
- **Perplexity AI API Key**

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd AWS_AI_MANAGER
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   # Create .env file
   echo "PERPLEXITY_API_KEY=your_api_key_here" > .env
   ```

5. **Run the application**:
   ```bash
   streamlit run streamlit_app.py
   ```

## 💬 Usage Examples

### EC2 Instance Management

**Basic Instance Creation:**
```
"create an ec2 instance"
```
*System Response:* Asks for name, AMI, and instance type with suggestions

**Advanced Configuration:**
```
"create t3.medium instance named web-prod with 100GB gp3 storage"
```
*System Response:* Extracts parameters and confirms configuration

### RDS Database Management

**Simple Database:**
```
"create a postgres database"
```
*System Response:* Guides through all required parameters step-by-step

**Production Database:**
```
"create production postgres 14 database with 200GB storage"
```
*System Response:* Handles complex requirements with appropriate suggestions

### S3 Bucket Operations

**Basic Bucket:**
```
"create a bucket for my website"
```
*System Response:* Suggests naming conventions and configuration options

### DynamoDB Table Creation

**Simple Table:**
```
"create a users table with email as primary key"
```
*System Response:* Handles schema definition with type suggestions

## 🔧 Configuration

### Environment Variables

```bash
# Required
PERPLEXITY_API_KEY=your_perplexity_api_key

# Optional
AWS_DEFAULT_REGION=us-east-1
STREAMLIT_SERVER_PORT=8501
```

### AWS Permissions

Ensure your AWS credentials have the following permissions:
- EC2: `ec2:*`
- RDS: `rds:*`
- S3: `s3:*`
- DynamoDB: `dynamodb:*`
- IAM: `iam:*`

## 🔒 Security Considerations

### ⚠️ Important Security Notes

**RDS Security Groups:**
The default RDS configuration allows broad inbound access for demonstration purposes. **Never use in production without modifying security groups.**

**API Key Protection:**
- Store Perplexity API key securely in `.env`
- Never commit API keys to version control
- Use environment-specific key management

**AWS Credentials:**
- Use IAM roles with minimal required permissions
- Implement credential rotation policies
- Monitor resource usage and costs

## 🐛 Troubleshooting

### Common Issues

**Parameter Extraction Not Working:**
- Check that all required parameters are being requested
- Verify conversation flow isn't skipping steps
- Ensure suggestions are appearing for each parameter

**Terraform Errors:**
- Verify AWS credentials are properly configured
- Check Terraform version compatibility
- Ensure required AWS permissions are granted

**AI Response Issues:**
- Verify Perplexity API key is valid
- Check internet connectivity
- Monitor API rate limits

### Debug Mode

Enable debug logging:
```bash
export STREAMLIT_DEBUG=true
streamlit run streamlit_app.py
```

## 📊 Performance & Monitoring

### Metrics Tracked
- Conversation success rates
- Parameter extraction accuracy
- Terraform deployment times
- User interaction patterns

### Optimization Features
- Caching for frequent queries
- Asynchronous processing for long operations
- Intelligent resource suggestions based on usage history

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. **Run tests**:
   ```bash
   python -m pytest
   ```

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints for new functions
- Include comprehensive docstrings
- Write unit tests for new features

### Pull Request Process

1. Update documentation for any new features
2. Add tests for new functionality
3. Ensure all tests pass
4. Update version in `setup.py` if applicable

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Perplexity AI** for advanced language model capabilities
- **Streamlit** for the excellent web application framework
- **Terraform** for infrastructure as code automation
- **AWS** for comprehensive cloud services

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the conversation examples

---

**Happy AWS Managing! 🚀**

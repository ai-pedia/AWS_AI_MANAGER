import boto3
import json
from typing import Dict, List, Any
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

class AWSEnvironmentInfo:
    """
    Fetches user-specific AWS environment information for personalized welcome messages
    """

    def __init__(self):
        self.ec2 = None
        self.rds = None
        self.s3 = None
        self.iam = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AWS clients with error handling"""
        try:
            self.ec2 = boto3.client('ec2')
            self.rds = boto3.client('rds')
            self.s3 = boto3.client('s3')
            self.iam = boto3.client('iam')
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"AWS credentials not found: {e}")
        except Exception as e:
            print(f"Error initializing AWS clients: {e}")

    def get_available_availability_zones(self) -> List[str]:
        """Get available availability zones in the current region"""
        if not self.ec2:
            return ['us-east-1a', 'us-east-1b', 'us-east-1c']  # Default fallback

        try:
            response = self.ec2.describe_availability_zones()
            zones = [zone['ZoneName'] for zone in response['AvailabilityZones'] if zone['State'] == 'available']
            return zones[:3]  # Return first 3 available zones
        except ClientError as e:
            print(f"Error fetching availability zones: {e}")
            return ['us-east-1a', 'us-east-1b', 'us-east-1c']

    def get_supported_rds_versions(self, engine: str = 'postgres') -> List[str]:
        """Get supported RDS engine versions"""
        if not self.rds:
            return ['15.3', '14.5', '13.4']  # Default fallback

        try:
            response = self.rds.describe_db_engine_versions(Engine=engine)
            versions = [version['EngineVersion'] for version in response['DBEngineVersions']]
            # Return latest 3 versions
            return sorted(versions, reverse=True)[:3]
        except ClientError as e:
            print(f"Error fetching RDS versions for {engine}: {e}")
            return ['15.3', '14.5', '13.4']

    def get_existing_resources_count(self) -> Dict[str, int]:
        """Get count of existing resources (consistent with list functions)"""
        counts = {'ec2': 0, 'rds': 0, 's3': 0, 'dynamodb': 0, 'iam_users': 0, 'iam_roles': 0}

        try:
            # Count only RUNNING and PENDING EC2 instances (same as list_ec2)
            if self.ec2:
                ec2_response = self.ec2.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'pending']}]
                )
                counts['ec2'] = sum(len(reservation['Instances']) for reservation in ec2_response.get('Reservations', []))

            # Count only AVAILABLE RDS instances (same as list_rds_instances)
            if self.rds:
                rds_response = self.rds.describe_db_instances()
                available_rds = [db for db in rds_response.get('DBInstances', [])
                               if db.get('DBInstanceStatus') in ['available', 'creating', 'modifying']]
                counts['rds'] = len(available_rds)

            if self.s3:
                s3_response = self.s3.list_buckets()
                counts['s3'] = len(s3_response.get('Buckets', []))

            if self.iam:
                iam_users = self.iam.list_users()
                iam_roles = self.iam.list_roles()
                counts['iam_users'] = len(iam_users.get('Users', []))
                counts['iam_roles'] = len(iam_roles.get('Roles', []))

        except ClientError as e:
            print(f"Error fetching resource counts: {e}")

        return counts

    def get_region_info(self) -> str:
        """Get current AWS region"""
        try:
            # Try to get region from any client
            if self.ec2:
                return self.ec2.meta.region_name
            elif self.rds:
                return self.rds.meta.region_name
            elif self.s3:
                return self.s3.meta.region_name
            elif self.iam:
                return self.iam.meta.region_name
        except:
            pass
        return "us-east-1"  # Default fallback

    def get_environment_summary(self) -> Dict[str, Any]:
        """Get comprehensive environment summary"""
        return {
            'region': self.get_region_info(),
            'availability_zones': self.get_available_availability_zones(),
            'rds_versions': {
                'postgres': self.get_supported_rds_versions('postgres'),
                'mysql': self.get_supported_rds_versions('mysql'),
                'aurora': self.get_supported_rds_versions('aurora-mysql')
            },
            'resource_counts': self.get_existing_resources_count(),
            'has_credentials': self.ec2 is not None
        }

# Global instance
aws_env = AWSEnvironmentInfo()

def get_aws_environment_info() -> Dict[str, Any]:
    """Get AWS environment information for welcome message"""
    return aws_env.get_environment_summary()

def generate_dynamic_welcome_message() -> str:
    """Generate a personalized welcome message based on AWS environment"""
    try:
        env_info = get_aws_environment_info()

        if not env_info['has_credentials']:
            return """
🎉 **Welcome to AWS AI Manager!** 🚀

I'm your intelligent AWS companion that makes cloud management effortless through natural language conversations.

## ⚠️ AWS Credentials Not Found
To get the most out of me, please configure your AWS credentials:
```bash
aws configure
```

## 💡 What I Can Do For You:
- **Create** EC2 instances, RDS databases, S3 buckets, DynamoDB tables
- **Modify** existing resources with intelligent parameter suggestions
- **Destroy** resources safely with confirmation
- **List** and monitor your AWS infrastructure

**Ready to get started? Just tell me what AWS resource you'd like to work with!** 🌟
"""

        # Dynamic welcome message with real AWS data
        region = env_info['region']
        zones = env_info['availability_zones']
        postgres_versions = env_info['rds_versions']['postgres']
        mysql_versions = env_info['rds_versions']['mysql']
        resource_counts = env_info['resource_counts']

        return f"""
🎉 **Welcome to AWS AI Manager!** 🚀

Managing resources in **{region}** • {resource_counts['ec2']} EC2 • {resource_counts['rds']} RDS • {resource_counts['s3']} S3

## 💡 **Quick Examples:**
- `"create ec2 in {zones[0]}"` (available: {', '.join(zones)})
- `"create postgres {postgres_versions[0]} database"`
- `"create bucket for my-app-data"`
- `"list all ec2 instances"`
- `"list my s3 buckets"`
- `"modify ec2 instance i-1234567890abcdef0 to change volume size"`
- `"destroy s3 bucket my-old-bucket"`
- `"estimate cost for running 3 t3.micro instances"`

**Tell me what you need in plain English!** 🌟
"""

    except Exception as e:
        print(f"Error generating dynamic welcome message: {e}")
        # Fallback to static message
        return """
🎉 **Welcome to AWS AI Manager!** 🚀

I'm your intelligent AWS companion that makes cloud management effortless through natural language conversations.

## 💡 What I Can Do For You:
- **Create** EC2 instances, RDS databases, S3 buckets, DynamoDB tables
- **Modify** existing resources with intelligent parameter suggestions
- **Destroy** resources safely with confirmation
- **List** and monitor your AWS infrastructure

## 💡 **Quick Examples:**
- `"create ec2 named my-server with t2.micro"`
- `"create postgres database with 20GB storage"`
- `"create bucket for my-app-data"`
- `"list all ec2 instances"`
- `"list my s3 buckets"`
- `"modify ec2 instance i-1234567890abcdef0 to change volume size"`
- `"destroy s3 bucket my-old-bucket"`
- `"estimate cost for running 3 t3.micro instances"`

**Ready to get started? Just tell me what AWS resource you'd like to work with!** 🌟
"""

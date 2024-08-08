import boto3
import pandas as pd

def get_all_regions():
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    regions = ec2_client.describe_regions()
    return [region['RegionName'] for region in regions['Regions']]

def get_ec2_details_from_region(region):
    ec2_client = boto3.client('ec2', region_name=region)
    ec2_list = []

    try:
        ec2_resources = ec2_client.describe_instances()
        for reservation in ec2_resources["Reservations"]:
            for instance_info in reservation["Instances"]:
                instance_id = instance_info.get("InstanceId", "N/A")
                instance_type = instance_info.get("InstanceType", "N/A")
                key_name = instance_info.get("KeyName", "N/A")
                private_ip = instance_info.get("PrivateIpAddress", "N/A")
                platform_details = instance_info.get("PlatformDetails", "N/A")
                state = instance_info.get("State", {}).get("Name", "N/A")
                monitoring = instance_info.get("Monitoring", {}).get("State", "N/A")
                # Identify root volume
                root_volume_id = None
                for volume in instance_info.get("BlockDeviceMappings", []):
                    if volume.get("DeviceName") in ['/dev/xvda', '/dev/sda1']:  # Adjust based on your needs
                        root_volume_id = volume.get("Ebs", {}).get("VolumeId", "N/A")
                        break                
                tags = {tag['Key']: tag['Value'] for tag in instance_info.get("Tags", [])}
                name = tags.get("Name", "N/A")

                ec2_asset = {
                    "Name": name,
                    "Instance_Id": instance_id,
                    "Instance_Type": instance_type,
                    "State": state,
                    "Instance_KeyPair": key_name,
                    "Instance_PrivateIp": private_ip,
                    "Instance_Platform": platform_details,
                    "Monitor": monitoring,
                    "Root_Volume_Id": root_volume_id,
                    "Region": region
                }
                ec2_list.append(ec2_asset)

    except KeyError as e:
        print(f"KeyError in region {region}: {e}")
    except Exception as e:
        print(f"An error occurred in region {region}: {e}")

    return ec2_list

def get_asg_details_from_region(region):
    asg_client = boto3.client('autoscaling', region_name=region)
    elb_client = boto3.client('elbv2', region_name=region)
    asg_list = []
    try:
        asg_resources = asg_client.describe_auto_scaling_groups()
        for asg in asg_resources['AutoScalingGroups']:
            asg_name = asg.get("AutoScalingGroupName", "N/A")
            launch_template = asg.get("LaunchTemplate", {}).get("LaunchTemplateName", "N/A")
            instance_count = len(asg.get("Instances", []))
            status = asg.get("HealthCheckType", "N/A")
            desired_capacity = asg.get("DesiredCapacity", "N/A")
            min_size = asg.get("MinSize", "N/A")
            max_size = asg.get("MaxSize", "N/A")
            asg_az = asg.get("AvailabilityZones", "N/A")
            target_groups = []
            for asg_lc in asg.get('TargetGroupARNs', []):
                tg_info = elb_client.describe_target_groups(TargetGroupArns=[asg_lc])
                target_groups.extend([tg['TargetGroupArn'] for tg in tg_info['TargetGroups']])
            asg_asset = {
                "ASG Name": asg_name,
                "Launch Template": launch_template,
                "Instances Count": instance_count,
                "Status": status,
                "Desired Capacity": desired_capacity,
                "Min": min_size,
                "Max": max_size,
                "Zone": asg_az,
                "Target Groups": ', '.join(target_groups)
            }

            asg_list.append(asg_asset)

    except KeyError as e:
        print(f"KeyError in region {region}: {e}")
    except Exception as e:
        print(f"An error occurred in region {region}: {e}")

    return asg_list

def get_rds_details_from_region(region):
    rds_client = boto3.client('rds', region_name=region)
    rds_list = []
    cluster_list = []
    try:
        rds_resources = rds_client.describe_db_instances()
        for rds in rds_resources['DBInstances']:
            rds_name = rds.get('DBInstanceIdentifier', "N/A")
            rds_instanceClass = rds.get('DBInstanceClass', 'N/A')
            engine = rds.get('Engine', 'N/A')
            engine_version = rds.get('EngineVersion', "N/A")
            status = rds.get('DBInstanceStatus', "N/A")
            storage = rds.get('AllocatedStorage', "N/A")
            zone = rds.get('AvailabilityZone', "N/A")
            multi_zone = rds.get('MultiAZ', "N/A")
            db_subnet_group = rds.get('DBSubnetGroup', {})
            vpc_id = db_subnet_group.get('VpcId', "N/A")

            rds_asset = {
                "DBInstanceIdentifier": rds_name,
                "InstanceClass": rds_instanceClass,
                "Engine": engine,
                "EngineVersion": engine_version,
                "Status": status,
                "AllocatedStorage": storage,
                "AvailabilityZone": zone,
                "MultiAZ": multi_zone,
                "VPCId": vpc_id            
                }            
            rds_list.append(rds_asset)
        clusters = rds_client.describe_db_clusters()
        for cluster in clusters['DBClusters']:
            cluster_id = cluster.get('DBClusterIdentifier', "N/A")
            cluster_status = cluster.get('Status', "N/A")
            cluster_engine = cluster.get('Engine', 'N/A')
            cluster_engine_version = cluster.get('EngineVersion', "N/A")
            cluster_endpoint = cluster.get('Endpoint', "N/A")
            cluster_reader_endpoint = cluster.get('ReaderEndpoint', "N/A")
            cluster_vpc_id = cluster.get('VpcId', "N/A")
            cluster_availability_zones = cluster.get('AvailabilityZones', [])

            cluster_asset = {
                "DBClusterIdentifier": cluster_id,
                "Status": cluster_status,
                "Engine": cluster_engine,
                "EngineVersion": cluster_engine_version,
                "Endpoint": cluster_endpoint,  # Primary endpoint (Writer)
                "ReaderEndpoint": cluster_reader_endpoint,  # Read-only endpoint
                "VPCId": cluster_vpc_id,
                "AvailabilityZones": cluster_availability_zones
            }
            cluster_list.append(cluster_asset)

    except Exception as e:
        print(f"An error occurred in region {region}: {e}")
    
    return rds_list, cluster_list

def main():
    all_ec2_details = []
    all_asg_details = []
    all_rds_details = []
    all_rds_clusters = []

    regions = get_all_regions()

    for region in regions:
        print(f"Searching EC2 data for region: {region}")
        region_ec2_details = get_ec2_details_from_region(region)
        all_ec2_details.extend(region_ec2_details)
        
        print(f"Searching ASG data for region: {region}")
        region_asg_details = get_asg_details_from_region(region)
        all_asg_details.extend(region_asg_details)

        print(f"Searching RDS data for region: {region}")
        region_rds_details, region_cluster_details  = get_rds_details_from_region(region)
        all_rds_details.extend(region_rds_details)
        all_rds_clusters.extend(region_cluster_details)

    
    return all_ec2_details, all_asg_details, all_rds_details, all_rds_clusters

# Call the main function and store the results
ec2_details, asg_details, rds_details, rds_clusters   = main()

# Convert to DataFrame and save to Excel
try:
    with pd.ExcelWriter('data.xlsx', engine='xlsxwriter') as writer:
        # Save EC2 details
        df_ec2 = pd.DataFrame(ec2_details)
        df_ec2.to_excel(writer, sheet_name="EC2_Details", index=False)
        
        # Save ASG details
        df_asg = pd.DataFrame(asg_details)
        df_asg.to_excel(writer, sheet_name="ASG_Details", index=False)

        # Save RDS details
        df_rds = pd.DataFrame(rds_details)
        df_rds.to_excel(writer, sheet_name="RDS_Details", index=False)

        # Save RDS_Cluster details
        df_rds = pd.DataFrame(rds_clusters)
        df_rds.to_excel(writer, sheet_name="RDS_Cluster_Details", index=False)
        
    print("Aws Inventory report has been generated and saved into 'data.xlsx'")
except Exception as e:
    print(f"An error occurred while saving the file: {e}")

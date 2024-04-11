from flask import Flask, render_template, request, redirect, url_for
import boto3
import datetime
from datetime import datetime, timezone, timedelta


app = Flask(__name__)
ec2 = boto3.resource('ec2')
cloudwatch = boto3.client('cloudwatch')

@app.route('/')
def index():
    instances = ec2.instances.all() 
    return render_template('index.html', instances=instances)


@app.route('/action', methods=['POST'])
def action():
    instance_id = request.form.get('id')
    action = request.form.get('action')
    
    instance = ec2.Instance(instance_id)
    
    if action == 'Detener':
        instance.stop()
    elif action == 'Iniciar':
        instance.start()
    
    return redirect(url_for('index'))


@app.route('/cpu_utilization', methods=['GET'])
def cpu_utilization():    

    if request.args.get('id'):
        instances_responses = get_metrics(request.args.get('id'))
    else:
        instances_responses = get_metrics(None)
    
    return render_template('cpu_utilization.html', instances_responses=instances_responses)


def get_metrics(instance_id):

    if instance_id:
        instances = ec2.instances.filter(InstanceIds=[instance_id])
    else:
        instances = ec2.instances.all() 

     # Obtener y formatear las fechas de ayer y hoy
    current_date = datetime.now(timezone.utc)
    current_date_f = current_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    yesterday_date = current_date - timedelta(days=1)
    yesterday_date_f = yesterday_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    instances_responses={}

    for instance in instances:
        
        # Configuracion de los parametros para el comando cloudwatch
        response = cloudwatch.get_metric_statistics(Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
        StartTime=yesterday_date_f,
        EndTime=current_date_f,
        Period=3600,
        Statistics=['Average'])

        #Ordenar los data_points por marca de tiempo
        data_points = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
        
        # Separar dia y hora, y agregarlos al json
        for data_point in data_points:
            fecha = data_point['Timestamp']
            data_point['Dia'] = fecha.strftime("%d-%m-%Y")
            data_point['Hora'] = fecha.strftime("%H:%M:%S")

        instances_responses[instance.id] = {
            'name': instance.tags[0]['Value'],
            'data_points': data_points
        }

    return instances_responses
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_emailotpverification'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailotpverification',
            name='purpose',
            field=models.CharField(default='registration', max_length=50),
            preserve_default=False,
        ),
    ]

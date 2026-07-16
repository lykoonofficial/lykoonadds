from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="repeat_after_hours",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text=(
                    "Kitne ghante baad ek user isi task ko dobara complete kar sakta hai. "
                    "Khaali chhodain agar yeh task har user sirf EK BAAR (hamesha ke liye) "
                    "complete kar sake, kabhi reset na ho."
                ),
            ),
        ),
        migrations.AlterUniqueTogether(
            name="adview",
            unique_together=set(),
        ),
    ]

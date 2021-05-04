
from django.dispatch import receiver
from django_geosource.signals import refresh_data_done

@receiver(refresh_data_done)
def clean_source_layer_config(sender, layer, source, **kwargs):
    print('REFRESH DATA DONE')
    source_instance = sender.objects.get(id=source)

    for source_layer in source_instance.layers.all():
        popup_config = source_layer.popup_config
        minisheet_config = source_layer.minisheet_config

        if not popup_config.get('advanced') and popup_config.get('wizard', {}).get('fields'):
            for i, field in enumerate(popup_config['wizard']['fields']):
                field_id = field.get('sourceFieldId')

                if not FilterField.objects.filter(field__id=field_id).exists():
                    popup_config['wizard']['fields'][i] = {}

            source_layer.popup_config = popup_config

        if not minisheet_config.get('advanced') and minisheet_config.get('wizard'):
            title = minisheet_config['wizard'].get('title', {})

            if not FilterField.objects.filter(id=title.get('sourceFieldId')):
                minisheet_config['wizard']['title'] = {}

            for i, field in enumerate(minisheet_config['wizard'].get('fields', [])):
                field_id = field.get('sourceFieldId')
                if not FilterField.objects.filter(field__id=field_id).exists():
                    minisheet_config['wizard']['fields'][i] = {}
            source_layer.minisheet_config = minisheet_config

        source_layer.save()

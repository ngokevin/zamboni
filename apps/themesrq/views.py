import jingo

from addons.models import Persona


def themesrq(request):
    themes = Persona.objects.filter(id__gte=2000, id__lte=2003)
    return jingo.render(request, 'themesrq/index.html', {
        'themes': themes
    })

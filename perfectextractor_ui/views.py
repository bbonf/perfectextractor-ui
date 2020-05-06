import csv
import tempfile
import os
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from .forms import MainForm
from .models import Corpus, Task
from .tasks import tasks
from perfectextractor.corpora.europarl.extractor import EuroparlPerfectExtractor, EuroparlPoSExtractor


def home(request):
    corpus = None
    if 'corpus' in request.GET:
        try:
            corpus = Corpus.objects.get(pk=request.GET['corpus'])
        except Corpus.DoesNotExist:
            pass
    form = MainForm(corpus=corpus)
    return render(request, 'home.html', dict(corpus=corpus, form=form))


def run_task(result_cb, extractor, path):
    def progress_cb(progress, total):
        result_cb(dict(progress=progress, total=total))

    extractor.process_folder(path, progress_cb=progress_cb)


def resolve_extractor(extractor):
    return {
        'pos': EuroparlPoSExtractor,
        'perfect': EuroparlPerfectExtractor}[extractor]


def run(request):
    form = MainForm(request.POST)
    if form.is_valid():
        kwargs = dict()
        for key in ['pos', 'lemmata']:
            entries = form.cleaned_data[key]
            if not isinstance(entries, list):
                entries = [entries]
            kwargs[key] = [entry for entry in entries if entry]

        outfile = tempfile.mktemp()
        kwargs['outfile'] = outfile
        kwargs['file_limit'] = form.cleaned_data.get('file_limit', 0)
        kwargs['output'] = form.cleaned_data.get('output_format')

        corpus = form.cleaned_data['corpus']
        source = form.cleaned_data['source']
        alignment = [os.path.basename(path) for path in form.cleaned_data['alignment']]
        extractor = resolve_extractor(form.cleaned_data['extractor'])(source, alignment, **kwargs)

        path = os.path.join(corpus.path, source)
        task_id = tasks.add(run_task, (extractor, path))
        Task.objects.filter(pk=task_id).update(outfile=outfile)
        return render(request, 'progress.html', dict(task_id=task_id,
                                                     source=source,
                                                     output_format=kwargs['output'],
                                                     alignment=alignment))
    else:
        return render(request, 'home.html', dict(form=form))


def status(request, task_id):
    return JsonResponse(dict(status=tasks.monitor(task_id)))


def csv_to_records(path, limit=10, delimiter=';'):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = iter(csv.reader(f, delimiter=delimiter))
        try:
            headers = next(reader)
        except StopIteration:
            return []

        data = []
        try:
            data = [next(reader) for i in range(limit)]
        except StopIteration:
            pass
        return [dict((headers[i], line[i]) for i in range(len(line))) for line in data]


def peek(request, task_id):
    outfile = Task.objects.get(pk=task_id).outfile
    head = csv_to_records(outfile)
    return JsonResponse(dict(head=head))


def download(request, task_id):
    outfile = Task.objects.get(pk=task_id).outfile
    contents = open(outfile, 'rb').read()
    response = HttpResponse(contents, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=results.csv'
    return response


def cancel(request, task_id):
    tasks.cancel(task_id)
    return JsonResponse(dict(success=True))
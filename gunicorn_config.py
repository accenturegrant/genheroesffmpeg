import multiprocessing

workers = multiprocessing.cpu_count() * 2 +1
bind = 'unix:genheroesffmpeg.sock'
umaas = 0o007
reload = True

#logging
accesslog = '_'
errorlog = '_'
# Rutti-Tutti-Find-A-Frutti

```
usage: rutti-tutti-find-a-frutti.py [-h] [--iwad IWAD] [--pwad PWAD]

Scan DOOM engine maps, scanning for possible medusa effects, and tutti-frutti errors.

optional arguments:
  -h, --help   show this help message and exit
  --iwad IWAD  filesystem path to the IWAD to use for resources
  --pwad PWAD  filesystem path to the PWAD to use for resources, and level scanning
```

Rutti-Tutti-Find-A-Frutti is a tool that attempts to find the most common issues with vanilla DOOM maps,
Medusa errors, and Tutti-Frutti errors. It does this by using the [Omgifol](https://github.com/devinacker/omgifol)
Python library in order to read maps, and scanning through linedefs. The code should be short and hopefully easy
to follow to determine the heuristics it uses.

I am not super knowledgable about DOOM editing, but it is my hope this tool may be useful for anyone creating vanilla
levels, so if you have any feedback or find it at all useful, please let me know!
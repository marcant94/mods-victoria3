# Descripciones del Workshop

Aquí se guardan las descripciones que se pegan en la página de Steam Workshop.
Steam **no lee nada** del mod, así que la descripción hay que subirla a mano:
estos `.txt` son la copia "fuente" para no tener que copiarla de la web cada vez.

Los archivos se generan a partir de los bloques `modifier` de las leyes, usando
las mismas cadenas de texto que el juego (los tooltips), así que siempre
coinciden con lo que se ve en partida.

## Regenerar

Desde la raíz del repositorio:

```bash
python3 tools/workshop_description.py "Modern Economy"
```

Escribe `workshop_en.txt` y `workshop_es.txt` en esta carpeta.

Opciones útiles:

```bash
# otra ruta de instalación del juego
python3 tools/workshop_description.py "Modern Economy" --game "/ruta/a/Victoria 3/game"

# otros idiomas (necesitan localización propia en el mod para los nombres de ley)
python3 tools/workshop_description.py "Modern Economy" --langs french german
```

## Notas

- La lista sale **en el orden del bloque `modifier` de cada ley**. Si quieres
  otro orden en Steam, reordena las líneas en el `.txt` de la ley (el orden no
  afecta al juego).
- Los modificadores booleanos (`..._bool = yes`) salen sin número; los `_add`
  en porcentaje salen como `+X%` según `common/modifier_type_definitions`.
- Los textos se resuelven con la localización del juego, incluidas las
  referencias `$...$`, `[Concept(...)]` y los iconos `@...!`, que se limpian
  para que quede texto plano válido para Steam.

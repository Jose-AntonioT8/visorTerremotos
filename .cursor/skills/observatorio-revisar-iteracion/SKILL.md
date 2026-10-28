---
name: observatorio-revisar-iteracion
description: >-
  Revisa lo hecho en la iteración recién terminada de un paso del observatorio
  sísmico y devuelve correcta, incorrecta o incompleta. Usar cuando el
  orquestador cierra una iteración, antes de dar el paso por terminado o de
  empezar el siguiente. Las skills de paso no la invocan.
disable-model-invocation: true
---

# Revisar la iteración

El agente invoca esta skill al terminar una iteración, antes de dar el paso por cerrado. Revisa el trabajo de esa iteración. No implementes, no corrijas y no abras el paso siguiente.

## Qué revisar

1. Parte `01`–`11` que el orquestador acaba de ejecutar. Si no la dice, mírala en el mensaje de la iteración. Si tampoco está, no revises el repositorio entero: responde `resultado: incompleta`.
2. En las partes 02 a 11, mira `git status` y `git diff`. En la parte 01 omite esa comprobación: el paso puede no tocar archivos y un diff vacío no es un fallo.
3. La skill del paso, su «Hecho cuando» y su «No hagas todavía».
4. Las comprobaciones de esa parte en [observatorio-verificar-parte](../observatorio-verificar-parte/SKILL.md). Léelas y aplícalas. No las sustituyas por una opinión. A partir de la parte 05, no apliques las comprobaciones de las partes 03 y 04.

## Qué tiene que cumplir el trabajo

- Los archivos tocados en las partes 02 a 11 corresponden a esa parte. Si la iteración adelantó el paso siguiente, falla.
- En las partes 02 a 11, lo que el agente dice haber hecho se ve en el diff o en una salida de comando. Una frase sin evidencia falla.
- La parte 01 queda `correcta` solo si el frontend está en http://localhost:4200 y el usuario ha confirmado los siete puntos del mapa. Sin esa confirmación, `incompleta`. No la cierres con una captura del agente.
- Se cumple el «Hecho cuando» del paso. Si falta una ejecución (Docker, SQL, navegador, descarga), el resultado es incompleta, no correcta.
- No hay secretos, `node_modules` ni GeoJSON grandes añadidos a Git.
- El país no sale de `place` y Angular no llama a USGS, si esos archivos se han tocado.

## Respuesta

La primera línea es exactamente una de estas:

```text
resultado: correcta
resultado: incorrecta
resultado: incompleta
```

Sigue con la parte, los archivos revisados y cada comprobación en `pasa`, `falla` o `sin evidencia`. Cierra con la lista de correcciones. Esta skill se invoca una vez por iteración, desde el orquestador. No la vuelvas a lanzar tú. Si el resultado no es `correcta`, el orquestador corrige y puede repetirla, con un tope de tres revisiones en total.

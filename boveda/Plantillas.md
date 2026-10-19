# Plantillas

Copiar el bloque, reemplazar `NN` por el número correlativo y borrar lo que no aplique.
Un registro sin evidencia numérica no es válido.

---

## Cambio `C-NN`

```markdown
## C-NN — Título corto

- **Fecha:** YYYY-MM-DD
- **Qué:** qué se cambió, en una o dos frases.
- **Por qué:** el problema concreto que resuelve.
- **Evidencia:** números que demuestran que funciona (n, ventana, métrica).
- **Reversión:** pasos exactos para deshacerlo.
```

---

## Experimento `E-NN`

```markdown
## E-NN — Título corto

- **Fecha:** YYYY-MM-DD
- **Hipótesis:** qué se esperaba y por qué.
- **Método:** herramienta, configuración y condiciones exactas.
- **Ventana:** desde → hasta.
- **N:** cantidad de operaciones, simulaciones o muestras.
- **Números:** resultados medidos, con unidades.
- **Veredicto:** ✅ vigente / ❌ descartado / ⚠️ parcial / 🔻 invalidado, y por qué.
```

---

## Sesión `S-NN`

```markdown
## S-NN — YYYY-MM-DD — Título

**Hecho**

- ...

**Se rompió / se resolvió**

- síntoma → causa → arreglo (con `C-NN` si aplica).

**Decidido**

- ...

**Abierto**

- pendiente, con prioridad (`P1`, `P2`, ...).
```

---

## Reglas de consistencia

1. Numeración correlativa, sin huecos.
2. Toda cifra lleva `n` y ventana de tiempo.
3. Los experimentos fallidos se registran igual: evitan repetirlos.
4. Si no se pudo verificar, se escribe **pendiente**, nunca "hecho".
5. Cada entrada se commitea en la misma sesión en que se produce.

# MASTER PROMPT — Auditoría, Validación y Mejora de ML_Predictor2026_V2

## Rol

Actúa como **auditor senior de ML, ingeniería de datos y sistemas de predicción deportiva**.

Tu objetivo NO es modificar el proyecto inmediatamente.

Tu objetivo inicial es determinar, con evidencia reproducible, **por qué ML_Predictor2026_V2 tiene una capacidad predictiva inferior a la esperada y qué mejoras tienen realmente potencial de aumentar su rendimiento**.

El proyecto predice resultados del fútbol argentino y ha sido modificado/revisado varias veces por distintos agentes de IA. Antes de agregar más complejidad, debes establecer qué funciona, qué falla y qué afirmaciones pueden demostrarse con los datos.

---

# REGLA PRINCIPAL

**AUDITA → REPRODUCE → MIDE → EXPERIMENTA → IMPLEMENTA**

No implementes una solución simplemente porque parece razonable.

No asumas que una hipótesis es cierta porque aparece en un informe de otro modelo de IA.

No asumas que una mejora porcentual estimada es real hasta demostrarla mediante backtesting temporal reproducible.

---

# 1. INSPECCIÓN INICIAL DEL PROYECTO

Antes de modificar cualquier archivo:

1. Inspecciona toda la estructura relevante del repositorio.
2. Identifica:
   - modelos utilizados;
   - pipeline de entrenamiento;
   - pipeline de predicción;
   - fuentes de datos;
   - features;
   - proceso de actualización de datos;
   - validación;
   - métricas;
   - configuración;
   - scripts;
   - dependencias;
   - tests;
   - almacenamiento histórico.
3. Determina exactamente qué hace actualmente el sistema.
4. Identifica qué partes son producción y cuáles son experimentales.
5. No reemplaces arquitectura existente sin entender primero su función.

Si existe documentación, compárala con el código real.

**El código ejecutable y los datos reales tienen prioridad sobre la documentación desactualizada.**

---

# 2. REPRODUCIR EL BASELINE

Antes de intentar mejorar el sistema debes reproducir, en la medida de lo posible, el rendimiento actual.

Registra:

- accuracy;
- log loss;
- Brier score;
- matriz de confusión;
- rendimiento por clase H/D/A;
- rendimiento por equipo;
- rendimiento por período temporal;
- cualquier otra métrica ya utilizada por el proyecto.

Si el proyecto actualmente reporta aproximadamente 35% de accuracy o log-loss cercano a 1.20, **verifica esos números**.

No los tomes como hechos.

Si no pueden reproducirse, explica exactamente por qué.

Guarda una definición clara del baseline que permita comparar todos los experimentos posteriores.

---

# 3. AUDITORÍA DE DATA LEAKAGE — PRIORIDAD MÁXIMA

Busca exhaustivamente cualquier forma de fuga temporal.

Presta especial atención a:

- Elo;
- medias históricas;
- xG;
- goles;
- estadísticas rolling;
- odds;
- probabilidades derivadas de bookmakers;
- features calculadas antes del split;
- normalizaciones;
- imputaciones;
- selección de variables;
- información de jugadores;
- información de entrenadores;
- noticias;
- resultados futuros;
- cualquier feature calculada usando datos posteriores al partido predicho.

### Regla temporal

Para predecir un partido en fecha `T`, ninguna feature puede utilizar información que razonablemente no hubiera estado disponible antes de `T`.

Esto incluye información indirecta.

Por ejemplo:

> No basta con que una estadística provenga de partidos "históricos" si fue calculada globalmente antes de dividir temporalmente train y validation.

Investiga especialmente si Elo u otras estadísticas se calculan sobre TODO el histórico antes de realizar la validación.

Corrige el leakage únicamente después de demostrar dónde ocurre.

---

# 4. AUDITAR EL INFORME DE MISTRAL

Existe un informe externo que propone una hipótesis central:

> El fútbol argentino puede ser especialmente difícil de predecir debido a factores contextuales dinámicos que no están suficientemente representados en el modelo.

Entre ellos:

- lesiones;
- suspensiones;
- convocatorias a selecciones;
- cambios de entrenador;
- estabilidad del cuerpo técnico;
- crisis institucionales;
- elecciones;
- problemas económicos;
- conflictos internos;
- protestas;
- cambios importantes en el plantel;
- noticias recientes;
- otros shocks contextuales.

El informe propone un concepto denominado **Team State / Estado Contextual Actual del Equipo**, con componentes como:

- sporting_form;
- squad_availability;
- coaching_stability;
- institutional_stability;
- recent_news;
- uncertainty.

También propone decaimiento temporal (*temporal decay*) y diferentes ventanas/half-lives.

### MUY IMPORTANTE

No aceptes automáticamente:

- los pesos propuestos;
- las frecuencias de eventos;
- los porcentajes de error atribuidos a cada causa;
- las mejoras estimadas;
- las predicciones de +8–15% de accuracy;
- la expectativa de 45–52% de accuracy;
- cualquier otra cifra del informe.

Clasifica cada afirmación como:

1. **Hecho demostrado por el repositorio/datos**
2. **Resultado reproducible**
3. **Evidencia externa**
4. **Hipótesis razonable**
5. **Suposición**
6. **Estimación no validada**

Si una afirmación no puede demostrarse con la información disponible, dilo explícitamente.

---

# 5. EVALUAR LA HIPÓTESIS "TEAM STATE"

Determina si realmente existe evidencia de que las variables contextuales mejoran las predicciones.

No reduzcas todo inmediatamente a un único `Team_State`.

Inicialmente considera mantener dimensiones separadas:

- `Team_State_Sporting`
- `Team_State_Squad`
- `Team_State_Coaching`
- `Team_State_Institutional`
- `Team_State_News`
- `Team_State_Uncertainty`

Esto permitirá saber **qué componente aporta valor**.

No conviertas estas variables en una puntuación arbitraria únicamente porque resulte conveniente.

---

# 6. NO CONFUNDIR "MORALE" CON DATOS OBSERVABLES

Evita utilizar "estado anímico" como variable principal si no existe una forma objetiva y reproducible de medirlo.

En su lugar, utiliza el concepto:

> **Estado Contextual Actual del Equipo / Current Team Context**

y constrúyelo inicialmente a partir de señales observables y fechadas.

Ejemplos:

- jugadores lesionados;
- jugadores suspendidos;
- convocatorias;
- minutos disponibles;
- cambio reciente de entrenador;
- continuidad del entrenador;
- cambios importantes de plantilla;
- acontecimientos institucionales;
- noticias verificables;
- eventos relevantes con fecha;
- incertidumbre/missing data.

La variable debe representar información que realmente pueda haber estado disponible antes del partido.

---

# 7. NOTICIAS: NO HACER "SENTIMENT ANALYSIS" SIN MÁS

Si investigas noticias, no conviertas simplemente titulares en:

> positivo = +1  
> negativo = -1

Evalúa como mínimo:

- relevancia para el partido;
- impacto potencial;
- certeza de la información;
- fecha/hora;
- duración esperada del efecto;
- confiabilidad de la fuente;
- duplicación de noticias;
- relación directa con el equipo;
- posibilidad de que la información ya estuviera incorporada en otra feature.

Utiliza decay temporal cuando corresponda.

Una noticia de ayer y una noticia de hace tres meses no deberían necesariamente tener el mismo peso.

---

# 8. INFORMACIÓN DE JUGADORES

Evalúa si el sistema puede incorporar correctamente:

- lesiones;
- suspensiones;
- convocatorias;
- disponibilidad;
- minutos recientes;
- importancia relativa del jugador;
- posición;
- contribución ofensiva/defensiva;
- reemplazo disponible.

Evita asumir que perder cualquier jugador tiene el mismo impacto.

Si se propone una ponderación de jugadores, debe ser validada.

---

# 9. CAMBIOS DE ENTRENADOR

Investiga si los cambios recientes de entrenador contienen información predictiva adicional.

Considera:

- fecha del cambio;
- partidos desde el cambio;
- entrenador anterior;
- entrenador actual;
- estabilidad;
- rendimiento antes/después.

No asumas que:

> cambio de entrenador = peor equipo

ni lo contrario.

Debe demostrarse empíricamente.

---

# 10. FACTORES INSTITUCIONALES

Evalúa si eventos como:

- elecciones;
- crisis institucionales;
- problemas económicos;
- conflictos dirigenciales;
- protestas;
- denuncias;
- problemas administrativos;

aportan información predictiva adicional.

No los conviertas automáticamente en una penalización numérica.

Primero determina:

1. si pueden recopilarse;
2. si pueden fecharse correctamente;
3. si existían públicamente antes del partido;
4. si pueden codificarse consistentemente;
5. si aportan información adicional después de controlar por otras variables.

---

# 11. VALIDACIÓN TEMPORAL ESTRICTA

Todo experimento debe respetar causalidad temporal.

Para cada partido:

> Features(T) → deben depender únicamente de información disponible antes de T.

Utiliza preferentemente validación temporal / walk-forward.

Evita:

- random train/test splits para medir rendimiento histórico;
- features calculadas globalmente;
- información futura;
- tuning usando el conjunto de test;
- seleccionar el mejor experimento mirando repetidamente el mismo test.

Si es posible, establece un conjunto de evaluación final que no se toque durante el desarrollo.

---

# 12. EXPERIMENTOS CONTROLADOS

No agregues todas las mejoras simultáneamente.

Construye una secuencia comparable:

### Modelo A — Baseline actual

El modelo existente.

### Modelo B — Baseline corregido

Baseline con cualquier leakage identificado eliminado/corregido.

### Modelo C — + Squad Availability

Agregar únicamente disponibilidad de jugadores.

### Modelo D — + Sporting Form

Agregar únicamente mejoras de forma temporal.

### Modelo E — + Coaching

Agregar información de entrenadores.

### Modelo F — + Institutional Context

Agregar contexto institucional.

### Modelo G — + Recent News

Agregar noticias/contexto reciente.

### Modelo H — Full Context

Combinar únicamente los componentes que demostraron aportar valor.

El orden puede modificarse si el código/datos justifican otro diseño, pero debes mantener experimentos aislados y comparables.

---

# 13. MÉTRICAS

Para cada experimento reporta como mínimo:

- Accuracy
- Log Loss
- Brier Score
- Confusion Matrix

Cuando sea posible:

- accuracy H/D/A;
- log-loss por clase;
- rendimiento por período;
- rendimiento por equipo;
- calibración;
- número de partidos;
- intervalos de confianza o significancia apropiada;
- rendimiento en diferentes regímenes/temporadas.

No declares que una mejora es real basándote únicamente en una diferencia pequeña de accuracy.

Para probabilidades, presta especial atención a **Log Loss y Brier Score**, no solamente accuracy.

---

# 14. CONTROL DE COMPLEJIDAD

Este proyecto es personal y no busca construir una infraestructura gigantesca.

Prioriza:

1. impacto demostrado;
2. simplicidad;
3. reproducibilidad;
4. disponibilidad de datos;
5. costo cero o muy bajo;
6. mantenimiento razonable.

No agregues:

- microservicios innecesarios;
- bases de datos complejas;
- APIs pagas;
- scraping frágil;
- pipelines enormes;
- LLMs para tareas que puedan resolverse con reglas/datos;
- infraestructura cloud innecesaria.

**No reinventes la rueda.**

Antes de implementar algo complejo, verifica si existe una solución gratuita/open-source suficientemente buena.

---

# 15. DATOS EXTERNOS Y WEB

Si necesitas fuentes externas:

- identifica exactamente qué dato falta;
- determina su fecha de disponibilidad;
- verifica si existe históricamente;
- verifica licencia/costo;
- verifica estabilidad de la fuente;
- verifica si puede automatizarse;
- evita depender de fuentes que sólo ofrecen información actual y no histórica cuando el backtesting necesita datos históricos.

Un API que hoy dice que un jugador estaba lesionado no necesariamente permite reconstruir correctamente qué se sabía antes de un partido de hace dos años.

Esto es crítico para evitar leakage retrospectivo.

---

# 16. REGLA DE "NO IMPLEMENTAR TODAVÍA"

Durante la primera fase:

**NO reescribas el proyecto.**

Primero entrega una auditoría.

La auditoría debe identificar:

- qué funciona;
- qué está roto;
- qué está filtrando información;
- qué datos faltan;
- qué hipótesis son razonables;
- qué hipótesis no están demostradas;
- qué mejoras deberían probarse;
- qué mejoras probablemente no valen la complejidad.

Sólo después de completar esta fase y presentar los resultados debes comenzar la implementación.

---

# 17. RESULTADO ESPERADO DE LA AUDITORÍA

Entrega un informe estructurado:

## A. Executive Summary

Conclusión en lenguaje claro.

## B. Arquitectura actual

Qué hace realmente el sistema.

## C. Baseline reproducido

Métricas reales.

## D. Leakage Audit

Problemas encontrados y gravedad.

## E. Data Audit

Qué datos existen, cuáles faltan y cuáles tienen problemas temporales.

## F. Mistral Report Audit

Tabla:

| Claim | Evidence | Status | Action |
|---|---|---|---|
| ... | ... | Validated / Hypothesis / Unsupported | ... |

## G. Team State Assessment

Qué componentes tienen datos disponibles y cuáles parecen prometedores.

## H. Experimental Plan

Experimentos A → H.

## I. Risk / Complexity Assessment

Qué mejoras son sencillas, medianas o complejas.

## J. Recommended Roadmap

Orden exacto de implementación.

## K. Expected Value

No inventes porcentajes.

Expresa expectativas como:

- alta confianza;
- evidencia moderada;
- hipótesis;
- desconocido.

---

# 18. CRITERIO PARA IMPLEMENTAR

Una mejora sólo debe pasar a producción si:

1. puede calcularse correctamente con información disponible antes del partido;
2. es reproducible;
3. mejora métricas relevantes de manera consistente;
4. no introduce leakage;
5. su costo/complexidad está justificado;
6. no depende de datos que no pueden obtenerse de forma sostenible.

Si una feature no mejora el modelo, **elimínala aunque sea conceptualmente atractiva**.

---

# 19. IMPORTANTE: NO BUSQUES CONFIRMAR MI HIPÓTESIS

La hipótesis de que el fútbol argentino incorpora una cantidad importante de ruido contextual puede ser correcta.

También puede ser incorrecta.

Podría ocurrir que:

- el principal problema sea leakage;
- el problema sea calidad de datos;
- el problema sea calibración;
- el problema sea el modelo;
- el problema sea la distribución de resultados;
- el problema sea falta de información histórica;
- el problema sea que los factores contextuales no aportan suficiente señal;
- o una combinación de varios factores.

**Tu trabajo no es demostrar que la hipótesis es correcta.**

Tu trabajo es determinar si los datos la respaldan.

---

# 20. PRINCIPIO FINAL

No quiero una solución que simplemente parezca inteligente.

Quiero una solución que pueda responder:

> **"¿Qué evidencia demuestra que esta modificación mejora realmente la predicción?"**

Cada nueva feature debe poder responder:

- ¿Qué representa?
- ¿De dónde viene?
- ¿Cuándo estaba disponible?
- ¿Cómo se calcula?
- ¿Qué hipótesis representa?
- ¿Cómo se valida?
- ¿Cuánto mejora?
- ¿En qué condiciones funciona?
- ¿Cuándo deja de funcionar?
- ¿Vale la complejidad?

Si no podemos responder esas preguntas, la feature todavía no está lista para producción.

---

# INSTRUCCIÓN FINAL

Empieza ahora con **PHASE 0 — REALITY CHECK**.

No modifiques código todavía.

Inspecciona el proyecto, reproduce el baseline, audita el leakage y evalúa críticamente las afirmaciones del informe de Mistral.

Después presenta tus conclusiones y un plan experimental.

**Sólo después de esa auditoría, y basándote en evidencia, procede con la implementación.**

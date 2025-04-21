# Simulación Completa de Formulario de Evaluación de Desempeño en Streamlit
# No requiere archivos externos, los datos están embebidos a partir de los Excel originales

import streamlit as st

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Inicializar Firebase solo una vez
if not firebase_admin._apps:
    cred_json = json.loads(st.secrets["GOOGLE_FIREBASE_CREDS"])
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)

# Conectar con Firestore
db = firestore.client()

# ─────────────────────────────────────────────────────────
# 📋 FORMULARIOS DE EVALUACIÓN - FORMATO ADAPTADO
# ─────────────────────────────────────────────────────────
formularios = {
    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 1 
    # ─────────────────────────────────────────────────────────
    1: [
        {'descripcion': 'Capacidad para establecer planes y programas, desagregando adecuadamente objetivos y metas que contribuyan al logro de los fines de la organización.',
         'factor': '1. PLANIFICACIÓN',
         'opciones': [
            ('a) Su planificación es altamente eficiente. Desagrega y establece objetivos y metas pertinentes a su área.', 4),
            ('b) Establece muy buenos programas y cursos de acción con objetivos y metas que favorecen el desarrollo del trabajo en su área.', 3),
            ('c) Planifica adecuadamente y establece objetivos y metas razonables.', 2),
            ('d) Presenta dificultades a la hora de desagregar y establecer planes, programas y cursos de acción adecuados. Se le hace difícil aplicar la planificación a la gestión.', 1),
            ('e) Planifica muy poco o establece planes, programas y cursos de acción poco eficaces para lograr los objetivos de su área.', 0)
         ]},
        {'descripcion': 'Capacidad para cumplir objetivos y metas de los planes y programas establecidos en su área.',
         'factor': '2. GESTIÓN DE PLANES Y PROGRAMAS',
         'opciones': [
            ('a) Logra el total cumplimiento eficaz de los objetivos y metas propuestos para su área en los plazos previstos.', 4),
            ('b) Logra buen cumplimiento de los objetivos y metas propuestos para su área dentro de los márgenes previstos.', 3),
            ('c) Logra que las metas propuestas dentro de su área se alcancen en los plazos previstos.', 2),
            ('d) Tiene dificultades para lograr que se cumplan las metas previstas en los plazos establecidos o, éstas, se alcanzan de manera parcial.', 1),
            ('e) Dificilmente logra concretar las metas previstas en los plazos establecidos para su área.', 0)
         ]},
        {'descripcion': 'Nivel de eficaz revisión del avance de la gestión de su área que le permite detectar desvíos significativos.',
         'factor': '3. CONTROL DE RESULTADOS',
         'opciones': [
            ('a) Controla de manera excelente la gestión de su área lo que le permite tomar casi siempre decisiones acertadas.', 4),
            ('b) Controla la gestión de su área de manera muy eficiente, lo que simplifica los procesos de evaluación y corrección.', 3),
            ('c) Realiza controles adecuados que permiten detectar oportunamente desvíos efectuando las correcciones necesarias.', 2),
            ('d) Sus controles son puntuales o excesivos con faltas evidentes en la fijación de prioridades.', 1),
            ('e) Rara vez evalúa y regula las tareas durante su ejecución. Su control final suele dejar elementos importantes sin verificar.', 0)
         ]},
        {'descripcion': 'Capacidad de relacionar y asignar recursos, controlando los factores que intervienen en el proceso de trabajo.',
         'factor': '4.1. ORGANIZAR EL TRABAJO',
         'opciones': [
            ('a) Excelente capacidad organizativa que le permite un dominio pleno de los factores que intervienen en el trabajo. Aún en situaciones de cambio permanente, reorganiza los recursos con máxima eficiencia.', 4),
            ('b) Tiene muy buena capacidad organizativa y de asignación de recursos. Supera los requerimientos normales del puesto.', 3),
            ('c) Organiza adecuadamente los procesos de trabajo normal y los mantiene bajo control.', 2),
            ('d) Escasa capacidad organizativa. En ocasiones no maneja adecuadamente los factores involucrados en el trabajo.', 1),
            ('e) Tiene problemas para integrar los factores de la producción.', 0)
         ]},
        {'descripcion': 'Capacidad de analizar y solucionar situaciones problemáticas.',
         'factor': '4.2. RESOLVER PROBLEMAS',
         'opciones': [
            ('a) Excelente habilidad para descomponer y analizar las situaciones problemáticas y para implementar las medidas adecuadas para solucionarlas.', 4),
            ('b) Muy buena capacidad para analizar y resolver los problemas de su área de modo que éstos no lo superen.', 3),
            ('c) Analiza y resuelve los problemas de rutina y evita complicaciones innecesarias. Puede requerir apoyo frente a problemas mayores.', 2),
            ('d) En ocasiones manifiesta dificultades para analizar los problemas y hallar soluciones factibles.', 1),
            ('e) Generalmente tiene dificultades para percibir los problemas. Le cuesta encontrar soluciones y tiende a transferir responsabilidades.', 0)
         ]},
        {'descripcion': 'Habilidad para dirigir personas o grupos de trabajo de modo que alcancen resultados de conjunto derivados de la coordinación realizada.',
         'factor': '5. CONDUCCIÓN',
         'opciones': [
            ('a) Excepcional habilidad para dirigir y coordinar grupos de trabajo. Criterio sobresaliente para delegar y desarrollar a su personal. Óptimos resultados de conjunto.', 4),
            ('b) Muy buen criterio para dirigir. Obtiene y mantiene buena integración de su personal y logra muy buenos resultados de su equipo.', 3),
            ('c) Es efectivo en la dirección y coordinación de su personal. Logra los objetivos fijados a través del trabajo conjunto.', 2),
            ('d) Suele tener dificultades para dirigir a su personal, delegar funciones y obtener un trabajo de conjunto.', 1),
            ('e) Continuamente presenta problemas para dirigir la acción de su personal, delegar funciones y obtener resultados adecuados de equipos.', 0)
         ]},
        {'descripcion': 'Habilidad para concretar los procesos de negociación iniciados.',
         'factor': '6.2. CERRAR TRANSACCIONES',
         'opciones': [
            ('a) Notable facilidad para conducir negociaciones y llegar a cierres exitosos con logros superiores a los previstos.', 4),
            ('b) Conduce habilidosamente y concreta los procesos de negociación con muy buenos resultados.', 3),
            ('c) Conduce y cierra satisfactoriamente procesos de negociación habituales.', 2),
            ('d) Puede iniciar y conducir transacciones pero tiene dificultades para cerrarlas satisfactoriamente. En algunas oportunidades requiere apoyo.', 1),
            ('e) Su actuación normalmente lleva a cierres confusos o inconvenientes que deben ser rectificados mediante la intervención de sus superiores.', 0)
         ]},
        {'descripcion': 'Capacidad para relacionarse eficazmente con el contexto, interno y externo, asumiendo la representación de su área.',
         'factor': '6.1 ASUMIR LA REPRESENTACIÓN INTERNA Y EXTERNA',
         'opciones': [
            ('a) Gran capacidad para relacionarse con el contexto y representar a su área. Establece con suma facilidad relaciones beneficiosas para la gestión de su unidad.', 4),
            ('b) Muy buena capacidad para representar a su área, estableciendo y manteniendo relaciones favorables para la gestión.', 3),
            ('c) Establece y mantiene relaciones convenientes para el accionar laboral de su área.', 2),
            ('d) A veces no asume adecuadamente la representación de su área. En algunas ocasiones sus relaciones no son beneficiosas y sus contactos pueden producir roces por falta de tacto y manejo.', 1),
            ('e) Tiene dificultades para establecer relaciones cuando asume la representación de su área. Sus contactos suelen ser conflictivos y hasta contraproducentes.', 0)
         ]},
        {'descripcion': 'Habilidad para leer la realidad de manera acorde a sus incumbencias y definir las fortalezas y oportunidades, así como las amenazas y debilidades para su área de influencia.',
         'factor': '7.1. INTERPRETACIÓN Y PREDICCIÓN DEL CONTEXTO',
         'opciones': [
            ('a) Optima lectura de la realidad, prediciendo con facilidad rumbos, ventajas y desventajas para su área.', 4),
            ('b) Realiza lecturas muy acertadas de la realidad en términos de ventajas y desventajas, fortalezas y debilidades para su área.', 3),
            ('c) Sus lecturas de la realidad son razonablemente correctas, lo que lo habilita para predecir con adecuado nivel de acierto.', 2),
            ('d) A menudo tiene dificultades para leer correctamente la realidad y demuestra escasa habilidad para predecir rumbos.', 1),
            ('e) Lectura habitualmente incorrecta de la realidad. Muestra escasa habilidad para predecir rumbos.', 0)
         ]},
        {'descripcion': 'Habilidad para aprovechar oportunidades provenientes del contexto interno o externo de la organización para la elaboración de los programas y planes de su área.',
         'factor': '7.2. MAXIMIZAR OPORTUNIDADES',
         'opciones': [
            ('a) Excelente habilidad para aprovechar oportunidades en la programación de su área.', 4),
            ('b) Aprovecha muy bien las oportunidades del contexto para obtener y aplicar ventajas para su área.', 3),
            ('c) Normalmente aprovecha oportunidades en la formulación de los planes y programas de su área.', 2),
            ('d) Escasamente aprovecha las oportunidades, se mantiene en la rutina y deja escapar situaciones que le permitirían obtener un mejor rendimiento de su área.', 1),
            ('e) Muy poco capaz de aprovechar oportunidades que resultarían claramente favorables para su área.', 0)
         ]},
        {'descripcion': 'Capacidad para pasar a la acción asumiendo riesgos para alcanzar objetivos, en los planes, programas y proyectos establecidos en su área.',
         'factor': '8. INICIATIVA',
         'opciones': [
            ('a) Notablemente capaz para generar acciones oportunas asumiendo los riesgos necesarios.', 4),
            ('b) Muy buena capacidad para actuar oportunamente asumiendo los riesgos necesarios.', 3),
            ('c) Actúa oportunamente asumiendo los riesgos necesarios.', 2),
            ('d) Ocasionalmente tiene problemas para actuar y asumir riesgos.', 1),
            ('e) Tiene dificultades para pasar a la acción y asumir los riesgos que ello implica.', 0)
         ]},
        {'descripcion': 'Capacidad para manejarse en situaciones que impliquen cambios o alteraciones en las actividades previstas y para generar cursos de acción efectivos, de acuerdo con las demandas cambiantes.',
         'factor': '9. ADAPTABILIDAD',
         'opciones': [
            ('a) Demuestra absoluta apertura para asimilar los cambios y para generar rápidamente cursos de acción eficaces en respuesta a los nuevos desafíos.', 4),
            ('b) Comprende los cambios rápidamente y sin dificultad, elaborando consecuentemente respuestas pertinentes.', 3),
            ('c) Es permeable a los cambios y reacciona razonablemente bien en la generación de cursos de acción adecuados.', 2),
            ('d) Le cuesta aceptar los cambios. Tiene dificultades para generar cursos de acción adecuados.', 1),
            ('e) Es muy poco permeable a las nuevas situaciones de trabajo. Difícilmente genera cursos de acción eficaces ante las nuevas situaciones.', 0)
         ]},
        {'descripcion': 'Capacidad para conducirse con decisión e independencia de criterio, administrando los intereses de la organización dentro del marco normativo y legal.',
         'factor': '10. AUTONOMÍA',
         'opciones': [
            ('a) Casi siempre se maneja con gran independencia, tomando las decisiones con total responsabilidad dentro de los límites de su función.', 4),
            ('b) Generalmente muestra independencia, tomando decisiones bajo su propia responsabilidad en la mayoría de las situaciones.', 3),
            ('c) Toma decisiones adecuadas a su función en situaciones usuales. En algunas ocasiones requiere apoyo de sus superiores o pares.', 2),
            ('d) Pocas veces exhibe una conducta autónoma. Con frecuencia solicita apoyo.', 1),
            ('e) Muy frecuentemente necesita consultar a sus superiores o pares para tomar decisiones.', 0)
         ]},
        {'descripcion': 'Grado de compromiso con los fines y metas de la organización.',
         'factor': '11. IDENTIFICACIÓN CON LA ORGANIZACIÓN',
         'opciones': [
            ('a) Su desempeño está permanentemente comprometido con los fines de la organización. Cuando critica siempre acompaña propuestas constructivas para mejorar el logro de dichos fines.', 4),
            ('b) Muy buen nivel de compromiso con los fines y metas de la organización.', 3),
            ('c) Adecuado compromiso con los fines y metas de la organización.', 2),
            ('d) Bajo compromiso con los fines de la organización. A veces parecen no importarle los problemas de la institución.', 1),
            ('e) Se compromete muy poco con los objetivos organizacionales y parece que siempre prevalecieran sus intereses o proyectos individuales.', 0)
         ]}
    ],

    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 2 
    # ─────────────────────────────────────────────────────────
    2: [
        {'descripcion': 'Aptitud para establecer planes y programas desagregando adecuadamente objetivos y metas que contribuyan al mejor desempeño de su sector.',
         'factor': '1. PLANIFICACIÓN',
         'opciones': [
            ('a) Su planificación es altamente eficiente. Desagrega y establece objetivos y metas pertinentes a su sector.', 4),
            ('b) Establece muy buenos planes y cursos de acción con objetivos y metas que favorecen el desarrollo del trabajo en su sector.', 3),
            ('c) Planifica adecuadamente y establece objetivos y metas razonables.', 2),
            ('d) Presenta dificultades para desagregar y establecer programas y cursos de acción adecuados para su sector.', 1),
            ('e) Planifica muy poco o establece programas y cursos de acción poco eficaces para lograr los objetivos de su sector.', 0)
         ]},
        {'descripcion': 'Capacidad para cumplir objetivos y controlar resultados de los programas y cursos de acción establecidos en su sector.',
         'factor': '2. GESTIÓN Y CONTROL DE PROGRAMAS Y PLANES',
         'opciones': [
            ('a) Excelente capacidad para cumplir eficazmente objetivos y controlar resultados de los programas y cursos de acción de su sector.', 4),
            ('b) Muy buena capacidad para alcanzar las metas propuestas y para controlar los resultados de los programas y cursos de acción establecidos para su sector.', 3),
            ('c) Logra cumplir las metas propuestas para su sector y controla adecuadamente los resultados.', 2),
            ('d) Tiene dificultades para lograr que se cumplan las metas previstas, así como para controlar adecuadamente los resultados de los programas y cursos de acción de su sector.', 1),
            ('e) Difícilmente logra concretar las metas previstas y su control suele ser ineficiente.', 0)
         ]},
        {'descripcion': 'Capacidad para lograr que el sector a su cargo trabaje con el máximo de eficiencia global haciendo un uso racional de los recursos asignados.',
         'factor': '3. ORGANIZACIÓN',
         'opciones': [
            ('a) Excelente capacidad organizativa que le permite administrar de manera excepcional los recursos. Logra la eficiencia global del equipo a su cargo.', 4),
            ('b) Tiene muy buena capacidad organizativa y de asignación de recursos, supera los requerimientos normales del puesto.', 3),
            ('c) Organiza adecuadamente los procesos de trabajo normal y los mantiene bajo control.', 2),
            ('d) Escasa capacidad organizativa. En ocasiones no maneja adecuadamente los factores involucrados en el trabajo del equipo a su cargo.', 1),
            ('e) Tiene dificultades para manejar adecuadamente los factores involucrados en el trabajo del equipo a su cargo y es ineficiente en el uso de los recursos.', 0)
         ]},
        {'descripcion': 'Habilidad para dirigir y coordinar personas o grupos de trabajo de modo que alcancen resultados de conjunto derivados de la coordinación realizada.',
         'factor': '4. CONDUCCIÓN',
         'opciones': [
            ('a) Excepcional habilidad para dirigir y coordinar equipos de trabajo. Criterio sobresaliente para desarrollar a su personal y delegar las tareas pertinentes.', 4),
            ('b) Muy buen criterio para dirigir y coordinar. Obtiene y mantiene la integración de su personal y logra muy buenos resultados de conjunto.', 3),
            ('c) Es efectivo para dirigir a su personal. Logra los objetivos fijados a través del trabajo conjunto.', 2),
            ('d) A veces presenta dificultades para coordinar a su personal, delegar funciones y obtener un trabajo en equipo.', 1),
            ('e) Continuamente tiene dificultades para dirigir y coordinar a su personal y para delegar funciones.', 0)
         ]},
        {'descripcion': 'Nivel de conocimiento profesional o técnico aplicado al eficaz ejercicio de la función y/o el puesto.',
         'factor': '5. COMPETENCIA PROFESIONAL PARA LA FUNCIÓN',
         'opciones': [
            ('a) Excelente nivel de formación y actualización que aplica eficientemente en todas las fases de su trabajo.', 4),
            ('b) Muy buen nivel de formación y actualización, realiza su trabajo con solvencia profesional.', 3),
            ('c) Sabe y aplica adecuadamente los conocimientos teóricos prácticos requeridos por su puesto. Necesita ser asesorado sólo en casos especiales.', 2),
            ('d) Tiene conocimientos limitados y/o los aplica con dificultad, lo que le permite cubrir sólo los mínimos requerimientos del puesto.', 1),
            ('e) Su nivel de conocimiento o su dominio para aplicarlos no le permiten desenvolverse en su trabajo adecuadamente.', 0)
         ]},
        {'descripcion': 'Capacidad para generar propuestas y poner en práctica acciones pertinentes en programas o proyectos fuera de las rutinas establecidas en su área.',
         'factor': '6. CREATIVIDAD',
         'opciones': [
            ('a) Notablemente capaz para generar permanentemente propuestas factibles de ser aplicadas.', 4),
            ('b) Muy buena capacidad para proponer enfoques novedosos y factibles y desarrollar su puesta en marcha.', 3),
            ('c) Es capaz de generar propuestas adecuadas ante las necesidades de trabajo.', 2),
            ('d) Ocasionalmente genera ideas o sugerencias dentro del área de su competencia.', 1),
            ('e) Tiene serias dificultades para generar propuestas novedosas y factibles.', 0)
         ]},
        {'descripcion': 'Capacidad para solucionar situaciones problemáticas.',
         'factor': '7. RESOLVER PROBLEMAS',
         'opciones': [
            ('a) Excelente habilidad para descomponer las situaciones problemáticas e implementar medidas adecuadas para solucionarlas.', 4),
            ('b) Muy buena capacidad para resolver los problemas de su área de modo que éstos no lo superen.', 3),
            ('c) Resuelve los problemas de rutina y evita complicaciones innecesarias. Puede requerir apoyo frente a problemas mayores.', 2),
            ('d) En ocasiones manifiesta dificultades para encarar los problemas y hallar soluciones factibles.', 1),
            ('e) Generalmente tiene dificultades para percibir los problemas. Le cuesta encontrar solución y transfiere las responsabilidades.', 0)
         ]},
        {'descripcion': 'Nivel de compromiso con la tarea que se mantiene aún en períodos difíciles a fin de lograr lo que se ha emprendido.',
         'factor': '8. INTERÉS POR EL TRABAJO',
         'opciones': [
            ('a) Excepcional compromiso. Se cuenta siempre con él en los momentos de mayor presión o dificultad.', 4),
            ('b) Muy buen nivel de compromiso con la tarea. En situaciones difíciles su interés no decae.', 3),
            ('c) Buen nivel de compromiso e interés por la tarea. Habitualmente se cuenta con su apoyo.', 2),
            ('d) Poco compromiso con la tarea. Su interés tiene tendencia a decaer en ocasiones en las que el trabajo debe realizarse bajo presión.', 1),
            ('e) Tiene serias dificultades para comprometerse con la tarea, su interés decae fácilmente.', 0)
         ]},
        {'descripcion': 'Preocupación por la actualización y desarrollo profesional propio y/o de sus colaboradores.',
         'factor': '9. ACTITUD FORMATIVA',
         'opciones': [
            ('a) Excelente predisposición para la actualización y formación, dentro de su competencia profesional. Aprovecha todas las oportunidades para mejorar sus conocimientos, aún con esfuerzo personal suplementario.', 4),
            ('b) Muy buena predisposición para la actualización y formación profesional. Aprovecha las oportunidades que se le presentan.', 3),
            ('c) Cumple con los requerimientos de actualización y formación profesional necesarios para el desempeño de su función.', 2),
            ('d) No demuestra especial interés por mejorar sus conocimientos profesionales, cuando lo hace es de manera ocasional y asistemática.', 1),
            ('e) No demuestra preocupación o compromiso por su actualización y formación profesional.', 0)
         ]},
        {'descripcion': 'Aptitud para identificar y definir problemas, discernir factores, causas y tendencias.',
         'factor': '10. CAPACIDAD ANALÍTICA',
         'opciones': [
            ('a) Sobresaliente por su aptitud analítica, lo que en el ejercicio de su especialidad le permite analizar y evaluar con suma precisión todos los factores involuntarios.', 4),
            ('b) Analiza integralmente las situaciones sometidas a su estudio, identificando y valorando sistemáticamente factores, componentes e implicancias', 3),
            ('c) Analiza satisfactoriamente las situaciones emergentes de su trabajo específico, tomando en cuenta los elementos determinantes.', 2),
            ('d) Suele presentar dificultades para analizar y relacionar los factores incluidos en las situaciones de trabajo habitual, requiere mucho esfuerzo para derivar conclusiones prácticas u operativas.', 1),
            ('e) Tiene grandes dificultades para valorar los hechos y sacar conclusiones.', 0)
         ]},
        {'descripcion': 'Habilidad para transmitir conocimientos, ideas o sugerencias.',
         'factor': '11. CAPACIDAD DE ASESORAMIENTO E INFORMACIÓN',
         'opciones': [
            ('a) Excelente aptitud para brindar información clara y precisa, y asesoramiento pertinente, oportuno y práctico.', 4),
            ('b) Buen nivel de asesoramiento. Sus intervenciones son siempre útiles y oportunas, y transmitidas en forma clara y precisa.', 3),
            ('c) Proporciona información y asesoramiento útil y transmite adecuadamente.', 2),
            ('d) Tiene dificultades para transmitir información con claridad y precisión, le cuesta brindarla oportunamente.', 1),
            ('e) Usualmente sus opiniones y asesoramiento son inadecuados y faltos de oportunidad y/ o su transmisión suele ser inadecuada.', 0)
         ]},
        {'descripcion': 'Capacidad para manejarse en situaciones que impliquen cambios o alteraciones en las actividades previstas, y para generar nuevos cursos de acción efectivos con demandas cambiantes.',
         'factor': '12. ADAPTABILIDAD',
         'opciones': [
            ('a) Encara con mucha soltura situaciones nuevas o cambiantes y siempre se involucra dinámicamente.', 4),
            ('b) Comprende los cambios rápidamente y sin dificultad, actuando consecuentemente en la elaboración de respuestas pertinentes.', 3),
            ('c) Es permeable a los cambios y reacciona razonablemente en la generación de los cursos de acción adecuados.', 2),
            ('d) Le cuesta asimilar los cambios. Tiene dificultad para generar cursos de acción adecuados.', 1),
            ('e) Es poco permeable a las nuevas situaciones de trabajo y muy poco capaz de adoptar cursos de acción adaptadas a ellas.', 0)
         ]}
    ],

    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 3 
    # ─────────────────────────────────────────────────────────
    3: [
        {'descripcion': 'Aptitud para establecer planes y programas desagregando adecuadamente objetivos y metas que contribuyan al mejor desempeño de su sector.',
         'factor': '1. PLANIFICACIÓN',
         'opciones': [
            ('a) Su planificación es altamente eficiente. Desagrega y establece objetivos y metas pertinentes a su sector.', 4),
            ('b) Establece muy buenos planes y cursos de acción con objetivos y metas que favorecen el desarrollo del trabajo en su sector.', 3),
            ('c) Planifica adecuadamente y establece objetivos y metas razonables.', 2),
            ('d) Presenta dificultades para desagregar y establecer programas y cursos de acción adecuados para su sector.', 1),
            ('e) Planifica muy poco o establece programas y cursos de acción poco eficaces para lograr los objetivos de su sector.', 0)
         ]},
        {'descripcion': 'Capacidad para cumplir objetivos y controlar resultados de los programas y cursos de acción establecidos en su sector.',
         'factor': '2. GESTIÓN Y CONTROL DE PROGRAMAS Y PLANES',
         'opciones': [
            ('a) Excelente capacidad para cumplir eficazmente objetivos y controlar resultados de los programas y cursos de acción de su sector.', 4),
            ('b) Muy buena capacidad para alcanzar las metas propuestas y para controlar los resultados de los programas y cursos de acción establecidos para su sector.', 3),
            ('c) Logra cumplir las metas propuestas para su sector y controla adecuadamente los resultados.', 2),
            ('d) Tiene dificultades para lograr que se cumplan las metas previstas, así como para controlar adecuadamente los resultados de los programas y cursos de acción de su sector.', 1),
            ('e) Difícilmente logra concretar las metas previstas y su control suele ser ineficiente.', 0)
         ]},
        {'descripcion': 'Capacidad para lograr que el sector a su cargo trabaje con el máximo de eficiencia global haciendo un uso racional de los recursos asignados.',
         'factor': '3. ORGANIZACIÓN',
         'opciones': [
            ('a) Excelente capacidad organizativa que le permite administrar de manera excepcional los recursos. Logra la eficiencia global del equipo a su cargo.', 4),
            ('b) Tiene muy buena capacidad organizativa y de asignación de recursos, supera los requerimientos normales del puesto.', 3),
            ('c) Organiza adecuadamente los procesos de trabajo normal y los mantiene bajo control.', 2),
            ('d) Escasa capacidad organizativa. En ocasiones no maneja adecuadamente los factores involucrados en el trabajo del equipo a su cargo.', 1),
            ('e) Tiene dificultades para manejar adecuadamente los factores involucrados en el trabajo del equipo a su cargo y es ineficiente en el uso de los recursos.', 0)
         ]},
        {'descripcion': 'Habilidad para dirigir y coordinar personas o grupos de trabajo de modo que alcancen resultados de conjunto derivados de la coordinación realizada.',
         'factor': '4. CONDUCCIÓN',
         'opciones': [
            ('a) Excepcional habilidad para dirigir y coordinar equipos de trabajo. Criterio sobresaliente para desarrollar a su personal y delegar las tareas pertinentes.', 4),
            ('b) Muy buen criterio para dirigir y coordinar. Obtiene y mantiene la integración de su personal y logra muy buenos resultados de conjunto.', 3),
            ('c) Es efectivo para dirigir a su personal. Logra los objetivos fijados a través del trabajo conjunto.', 2),
            ('d) A veces presenta dificultades para coordinar a su personal, delegar funciones y obtener un trabajo en equipo.', 1),
            ('e) Continuamente tiene dificultades para dirigir y coordinar a su personal y para delegar funciones.', 0)
         ]},
        {'descripcion': 'Nivel de conocimiento técnicas y habilidades aplicados al eficaz ejercicio de la función y/o el puesto.',
         'factor': '5. COMPETENCIA PARA LA FUNCIÓN',
         'opciones': [
            ('a) Conoce plenamente el contenido de su función, domina los conocimientos, técnicas, habilidades y procedimientos requeridos, y los aplica con gran eficacia.', 4),
            ('b) Muy buen nivel de conocimientos, técnicas y habilidades y procedimientos requeridos para su función, que le permiten realizar su trabajo eficientemente.', 3),
            ('c) Conoce su cometido y realiza bien su trabajo habitual.', 2),
            ('d) Escaso nivel de conocimientos y habilidades requeridas. Su trabajo no siempre es satisfactorio.', 1),
            ('e) Su muy bajo nivel de conocimientos y habilidades requeridas le impiden desenvolverse en su trabajo adecuadamente.', 0)
         ]},
        {'descripcion': 'Capacidad para pasar a la acción asumiendo riesgos para alcanzar objetivos, en los programas establecidos en su sector.',
         'factor': '6. INICIATIVA',
         'opciones': [
            ('a) Notablemente capaz para generar acciones oportunas asumiendo los riesgos necesarios.', 4),
            ('b) Muy buena capacidad para actuar oportunamente asumiendo los riesgos necesarios.', 3),
            ('c) Actúa oportunamente asumiendo los riesgos necesarios.', 2),
            ('d) Ocasionalmente tiene problemas para actuar y asumir riesgos.', 1),
            ('e) Tiene dificultades para pasar a la acción y asumir los riesgos que ello implica.', 0)
         ]},
        {'descripcion': 'Capacidad para solucionar situaciones problemáticas.',
         'factor': '7. RESOLVER PROBLEMAS',
         'opciones': [
            ('a) Excelente habilidad para descomponer las situaciones problemáticas e implementar medidas adecuadas para solucionarlas.', 4),
            ('b) Muy buena capacidad para resolver los problemas de su área de modo que éstos no lo superen.', 3),
            ('c) Resuelve los problemas de rutina y evita complicaciones innecesarias. Puede requerir apoyo frente a problemas mayores.', 2),
            ('d) En ocasiones manifiesta dificultades para encarar los problemas y hallar soluciones factibles.', 1),
            ('e) Generalmente tiene dificultades para percibir los problemas. Le cuesta encontrar soluciones y tiende a transferir las responsabilidades.', 0)
         ]},
        {'descripcion': 'Nivel de compromiso con la tarea que se mantiene aún en períodos difíciles a fin de lograr lo que se ha emprendido.',
         'factor': '8. INTERÉS POR EL TRABAJO',
         'opciones': [
            ('a) Excepcional compromiso. Se cuenta siempre con él en los momentos de mayor presión o dificultad.', 4),
            ('b) Muy buen nivel de compromiso con la tarea. En situaciones difíciles su interés no decae.', 3),
            ('c) Buen nivel de compromiso e interés por la tarea. Habitualmente se cuenta con su apoyo.', 2),
            ('d) Poco compromiso con la tarea. Su interés tiene tendencia a decaer en ocasiones en las que el trabajo debe realizarse bajo presión.', 1),
            ('e) Tiene serias dificultades para comprometerse con la tarea, su interés decae fácilmente.', 0)
         ]},
        {'descripcion': 'Preocupación por la formación y capacitación propia y/o de sus colaboradores.',
         'factor': '9. ACTITUD FORMATIVA',
         'opciones': [
            ('a) Considera que la formación y capacitación son esenciales, y trata de adquirirla y proporcionarla a sus subordinados de manera sistemática y permanente.', 4),
            ('b) Demuestra mucho interés en el desarrollo propio y de sus colaboradores, poniendo los medios necesarios para su consecución.', 3),
            ('c) Promueve su formación y la de sus colaboradores para el desarrollo del trabajo en su área.', 2),
            ('d) No pone especial interés en mejorar sus conocimientos ni los de sus colaboradores.', 1),
            ('e) Le da muy poca o ninguna importancia a la formación propia y a la de sus colaboradores.', 0)
         ]},
        {'descripcion': 'Habilidad para intercambiar en forma eficaz y permanente mensajes relativos a los intereses de la organización con superiores, pares, subordinados y terceros.',
         'factor': '10. COMUNICACIÓN',
         'opciones': [
            ('a) En general siempre establece una excelente comunicación con sus pares, superiores y subordinados, haciendo de ello un medio eficaz de trabajo.', 4),
            ('b) Muy buena habilidad para comunicarse con sus pares, superiores y subordinados. En su área se maneja información veraz y completa.', 3),
            ('c) Buena habilidad comunicativa, manejando la información adecuadamente en su área.', 2),
            ('d) A veces muestra deficiencias en la comunicación o presenta dificultades en el manejo de la información recibida y/o transmitida.', 1),
            ('e) Habitualmente tiene dificultades en la transmisión y utilización de la información recibida.', 0)
         ]},
        {'descripcion': 'Empeño por alcanzar los objetivos comunes en la realización del trabajo propio y en el interés por el de los demás.',
         'factor': '11. COLABORACIÓN',
         'opciones': [
            ('a) Ofrece permanentemente su colaboración ante cada circunstancia y problema. Su accionar constante inspira seguridad y confianza en el grupo de trabajo.', 4),
            ('b) Está muy dispuesto a colaborar. Casi siempre es requerido para aportar en la solución de problemas. Su actitud es reconocida y valorada.', 3),
            ('c) Colabora adecuadamente en los esfuerzos por alcanzar los objetivos comunes.', 2),
            ('d) Realiza aportes limitados y circunstanciales para la obtención de los objetivos comunes.', 1),
            ('e) Suele tener dificultades para colaborar con sus pares y superiores.', 0)
         ]},
        {'descripcion': 'Capacidad para manejarse en situaciones que impliquen cambios o alteraciones en las actividades previstas, y para generar nuevos cursos de acción efectivos de acuerdo con demandas cambiantes.',
         'factor': '12. ADAPTABILIDAD',
         'opciones': [
            ('a) Encara con mucha soltura situaciones nuevas o cambiantes y siempre se involucra dinámicamente.', 4),
            ('b) Comprende los cambios rápidamente y sin dificultad, actuando consecuentemente en la elaboración de respuestas pertinentes.', 3),
            ('c) Es permeable a los cambios y reacciona razonablemente en la generación de los cursos de acción adecuados.', 2),
            ('d) Le cuesta asimilar los cambios. Tiene dificultad para generar cursos de acción adaptados.', 1),
            ('e) Es poco permeable a las nuevas situaciones de trabajo y muy poco capaz de adoptar cursos de acción adaptados a ellas.', 0)
         ]}
    ],

    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 4 
    # ─────────────────────────────────────────────────────────
    4: [
        {'descripcion': 'Nivel de conocimiento profesional o técnico aplicado al eficaz ejercicio de la función y/o el puesto.',
         'factor': '1. COMPETENCIA PROFESIONAL PARA LA FUNCIÓN',
         'opciones': [
            ('a) Excelente nivel de formación y actualización que aplica eficientemente en todas las fases de su trabajo.', 4),
            ('b) Muy buen nivel de formación y actualización, realiza su trabajo con solvencia profesional.', 3),
            ('c) Posee y aplica adecuadamente los conocimientos teórico-prácticos requeridos por su puesto. Necesita ser asesorado sólo en casos especiales.', 2),
            ('d) Tiene conocimientos limitados y/o los aplica con dificultad, lo que le permite cubrir sólo los mínimos requerimientos del puesto.', 1),
            ('e) Su nivel de conocimientos o su dominio para aplicarlos no le permiten desenvolverse en su trabajo adecuadamente.', 0)
         ]},
        {'descripcion': 'Capacidad para generar propuestas y poner en práctica acciones pertinentes en programas o proyectos fuera de las rutinas establecidas en su área.',
         'factor': '2. CREATIVIDAD',
         'opciones': [
            ('a) Notablemente capaz para generar permanentemente propuestas factibles de ser aplicadas.', 4),
            ('b) Muy buena capacidad para proponer enfoques novedosos y factibles, y desarrollar su puesta en marcha.', 3),
            ('c) Es capaz de generar propuestas adecuadas ante las necesidades de trabajo.', 2),
            ('d) Ocasionalmente genera ideas o sugerencias dentro del área de su competencia.', 1),
            ('e) Tiene serias dificultades para generar propuestas novedosas y factibles.', 0)
         ]},
        {'descripcion': 'Capacidad para solucionar situaciones problemáticas.',
         'factor': '3. RESOLVER PROBLEMAS',
         'opciones': [
            ('a) Excelente habilidad para descomponer las situaciones problemáticas e implementar medidas adecuadas para solucionarlas.', 4),
            ('b) Muy buena capacidad para resolver los problemas de su área de modo que éstos no lo superen.', 3),
            ('c) Resuelve los problemas de rutina y evita complicaciones innecesarias. Puede requerir apoyo frente a problemas mayores.', 2),
            ('d) En ocasiones manifiesta dificultades para encarar los problemas y hallar soluciones factibles.', 1),
            ('e) Generalmente tiene dificultades para percibir los problemas. Le cuesta encontrar soluciones y tiende a transferir responsabilidades.', 0)
         ]},
        {'descripcion': 'Aptitud para completar tareas y responsabilidades asignadas de acuerdo a metas y plazos originalmente pactados.',
         'factor': '4. CUMPLIMIENTO CON EL TRABAJO',
         'opciones': [
            ('a) Optimo cumplimiento en tiempo y forma de todas las tareas que se le encargan con excelentes resultados.', 4),
            ('b) Buen manejo de los plazos de tiempo y muy buenos resultados en el cumplimiento de las metas de trabajo.', 3),
            ('c) Normalmente cumple en término con sus trabajos y logra resultados adecuados.', 2),
            ('d) Es irregular en el cumplimiento de su trabajo. En ocasiones no respeta los plazos y, a veces, compromete la calidad de su producción.', 1),
            ('e) No completa adecuadamente sus trabajos o los realiza fuera de término. Casi siempre encuentra dificultades que le impiden el cumplimiento de los plazos.', 0)
         ]},
        {'descripcion': 'Aptitud para identificar y definir problemas, discernir factores, causas y tendencias.',
         'factor': '5. CAPACIDAD ANALÍTICA',
         'opciones': [
            ('a) Sobresaliente aptitud analítica lo que, en el ejercicio de su especialidad, le permite analizar y evaluar con suma precisión todos los factores involucrados.', 4),
            ('b) Analiza integralmente las situaciones sometidas a su estudio, identificando y valorando sistemáticamente factores, componentes e implicancias.', 3),
            ('c) Analiza satisfactoriamente las situaciones emergentes de su trabajo específico, tomando en cuenta los elementos determinantes.', 2),
            ('d) Suele presentar dificultades para analizar y relacionar los factores incluidos en las situaciones de trabajo habitual, requiere mucho esfuerzo para derivar conclusiones prácticas u operativas.', 1),
            ('e) Tiene dificultades para analizar integralmente los factores involucrados y sacar conclusiones pertinentes.', 0)
         ]},
        {'descripcion': 'Habilidad para transmitir conocimientos, ideas o sugerencias.',
         'factor': '6. CAPACIDAD DE ASESORAMIENTO E INFORMACIÓN',
         'opciones': [
            ('a) Excelente aptitud para brindar información clara y precisa, y asesoramiento pertinente, oportuno y práctico.', 4),
            ('b) Buen nivel de asesoramiento. Sus intervenciones son siempre útiles y oportunas, y transmitidas en forma clara y precisa.', 3),
            ('c) Proporciona información y asesoramiento útil. Transmite adecuadamente.', 2),
            ('d) Tiene dificultades para transmitir información con claridad y precisión, le cuesta brindarla oportunamente.', 1),
            ('e) Usualmente sus opiniones y asesoramiento son inadecuados y faltos de oportunidad y/o su transmisión suele ser ineficaz.', 0)
         ]},
        {'descripcion': 'Preocupación por la actualización y desarrollo profesional.',
         'factor': '7. ACTITUD FORMATIVA',
         'opciones': [
            ('a) Excelente predisposición para la actualización y formación. Aprovecha todas las oportunidades para mejorar sus conocimientos.', 4),
            ('b) Muy buena predisposición para la actualización y formación profesional. Aprovecha las oportunidades que se le presentan.', 3),
            ('c) Cumple con los requerimientos de actualización y formación profesional necesarios para el cumplimiento de su función.', 2),
            ('d) No demuestra especial interés por mejorar sus conocimientos profesionales, cuando lo hace es de manera ocasional y asistemática.', 1),
            ('e) No demuestra preocupación o compromiso por su actualización y formación profesional.', 0)
         ]},
        {'descripcion': 'Nivel de compromiso con la tarea que se mantiene aún en períodos difíciles a fin de lograr lo que se ha emprendido.',
         'factor': '8. INTERÉS POR EL TRABAJO',
         'opciones': [
            ('a) Excepcional compromiso. Se cuenta siempre con él en los momentos de mayor presión o dificultad.', 4),
            ('b) Muy buen nivel de compromiso con la tarea. En situaciones difíciles su interés no decae.', 3),
            ('c) Buen nivel de compromiso e interés por la tarea. Habitualmente se cuenta con su apoyo.', 2),
            ('d) Poco compromiso con la tarea. Su interés tiene tendencia a decaer en ocasiones en las que el trabajo debe realizarse bajo presión.', 1),
            ('e) Tiene serias dificultades para comprometerse con la tarea, su interés decae fácilmente.', 0)
         ]},
        {'descripcion': 'Aptitud para alcanzar los objetivos comunes a través del trabajo propio y en equipo.',
         'factor': '9. COLABORACIÓN',
         'opciones': [
            ('a) Excelente colaborador con sus superiores y pares, gran facilidad para integrarse activamente en equipos de trabajo.', 4),
            ('b) Muy buena disposición para colaborar individualmente o cuando integra grupos de trabajo.', 3),
            ('c) Buen colaborador, se integra adecuadamente en equipos de trabajo.', 2),
            ('d) A veces poco dispuesto a colaborar, le cuesta integrarse en equipo.', 1),
            ('e) Suele tener dificultades para colaborar con sus pares y equipos.', 0)
         ]},
        {'descripcion': 'Capacidad para manejarse en situaciones que impliquen cambios o alteraciones en las actividades previstas, y para generar nuevos cursos de acción.',
         'factor': '10. ADAPTABILIDAD',
         'opciones': [
            ('a) Encara con mucha soltura situaciones nuevas o cambiantes y siempre se involucra dinamicamente.', 4),
            ('b) Comprende los cambios rápidamente y sin dificultad, actuando consecuentemente en la elaboración de respuestas pertinentes.', 3),
            ('c) Es permeable a los cambios y reacciona razonablemente en la generación de los cursos de acción adecuados.', 2),
            ('d) Le cuesta asimilar los cambios. Tiene dificultad para generar cursos de acción adecuados.', 1),
            ('e) Es poco permeable a las nuevas situaciones de trabajo y muy poco capaz de adoptar cursos de acción adaptados a ellas.', 0)
         ]}
    ],

    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 5 
    # ─────────────────────────────────────────────────────────
    5: [
        {'descripcion': 'Capacidad para lograr que el sector a su cargo trabaje con el máximo de eficiencia global haciendo un uso racional de los recursos asignados.',
         'factor': '1. ORGANIZACIÓN',
         'opciones': [
            ('a) Excelente capacidad organizativa que le permite administrar de manera excepcional los recursos. Logra la eficiencia global del equipo a su cargo.', 4),
            ('b) Tiene muy buena capacidad organizativa y de asignación de recursos, supera los requerimientos normales del puesto.', 3),
            ('c) Organiza adecuadamente los procesos de trabajo normal y los mantiene bajo control.', 2),
            ('d) Escasa capacidad organizativa. En ocasiones no maneja adecuadamente los factores involucrados en el trabajo del equipo a su cargo.', 1),
            ('e) Tiene dificultades para manejar adecuadamente los factores involucrados en el trabajo del equipo a su cargo y es ineficiente en el uso de los recursos.', 0)
         ]},
        {'descripcion': 'Habilidad para supervisar personas o grupos de trabajo de modo que alcancen resultados de conjunto.',
         'factor': '2. SUPERVISIÓN',
         'opciones': [
            ('a) Excepcional habilidad para supervisar personas o grupos de trabajo.', 4),
            ('b) Buen criterio para supervisar. Logra muy buenos resultados de conjunto.', 3),
            ('c) Logra un buen trabajo de conjunto. Tiene buen ascendente sobre su grupo.', 2),
            ('d) A veces presenta dificultades para supervisar a su personal y obtener resultados de conjunto.', 1),
            ('e) Continuamente tiene dificultades en la supervisión de su personal.', 0)
         ]},
        {'descripcion': 'Volumen de producción de acuerdo con los requerimientos del puesto en el tiempo acordado.',
         'factor': '3.1. CANTIDAD DE TRABAJO',
         'opciones': [
            ('a) Rendimiento excepcionalmente alto. Sobrepasa los márgenes requeridos normalmente en su puesto.', 4),
            ('b) Siempre alcanza y frecuentemente supera el rendimiento requerido en los plazos previstos.', 3),
            ('c) Alcanza los niveles normales de trabajo a un ritmo aceptable y en los plazos establecidos.', 2),
            ('d) Su rendimiento está por debajo de los niveles requeridos para el puesto, o no respeta los plazos establecidos.', 1),
            ('e) Su rendimiento está muy por debajo de los requerimientos y habitualmente no respeta los plazos establecidos.', 0)
         ]},
        {'descripcion': 'Nivel de terminación y perfección del trabajo que realiza. (Si la tarea es con atención al público se evalúa la correción en el trato con los usuarios y la adecuada satisfacción de las demandas).',
         'factor': '3.2. CALIDAD DE TRABAJO',
         'opciones': [
            ('a) Excepcional nivel de calidad de trabajo.', 4),
            ('b) Muy buen nivel de calidad de su trabajo.', 3),
            ('c) Adecuado nivel de calidad de su trabajo.', 2),
            ('d) Tiene dificultades para realizar su trabajo con la calidad requerida.', 1),
            ('e) Falta de calidad en la realización de su trabajo. Necesita constante monitoreo.', 0)
         ]},
        {'descripcion': 'Eficiente utilización del tiempo, materiales, procedimientos y métodos de trabajo.',
         'factor': '3.3. MANEJO DE RECURSOS',
         'opciones': [
            ('a) Excelente utilización de los recursos asignados a su puesto. Muy habilidoso para encontrar mejores métodos de trabajo y reducir costos.', 4),
            ('b) Muy efectivo para administrar recursos y reducir costos, mejorar métodos, procedimientos y técnicas.', 3),
            ('c) Buen sentido de la administración de los recursos. Uso adecuado de los métodos y técnicas.', 2),
            ('d) Tiene dificultades para administrar apropiadamente.', 1),
            ('e) No aprovecha los recursos asignados a su puesto, necesita constante monitoreo para administrar su tiempo y procedimientos de trabajo.', 0)
         ]},
        {'descripcion': 'Nivel de conocimientos requeridos para desempeñar las tareas relacionadas con el puesto.',
         'factor': '4. CONOCIMIENTO DE LAS TAREAS',
         'opciones': [
            ('a) Excepcional dominio de todas las fases de su trabajo y tareas relacionadas con el mismo.', 4),
            ('b) Buen dominio de las fases de su trabajo y sólidos conocimientos de sus tareas.', 3),
            ('c) Conoce adecuadamente su trabajo y las tareas relacionadas.', 2),
            ('d) Posee sólo los conocimientos elementales relacionados con su tarea.', 1),
            ('e) Conocimientos insuficientes para el desempleo de las tareas a su cargo.', 0)
         ]},
        {'descripcion': 'Capacidad para comprender y actuar de acuerdo a las pautas establecidas.',
         'factor': '5. CRITERIO',
         'opciones': [
            ('a) Excepcional capacidad para comprender las pautas de trabajo y actuar en consecuencia.', 4),
            ('b) Muy buena capacidad de comprensión de las pautas de trabajo, que le permite actuar minimizando los errores.', 3),
            ('c) Interpreta sin dificultad las pautas de trabajo y responde adecuadamente.', 2),
            ('d) Tiene dificultad para interpretar las pautas de trabajo y necesita frecuente monitoreo.', 1),
            ('e) Le cuesta comprender las pautas de trabajo y requiere una permanente indicación y monitoreo de la tarea.', 0)
         ]},
        {'descripcion': 'Disposición a cooperar con el superior y los demás empleados en la realización de tareas comunes.',
         'factor': '6. COLABORACIÓN',
         'opciones': [
            ('a) Excelente disposición a cooperar ante cada circunstancia o problema que se presente.', 4),
            ('b) Muy dispuesto a cooperar. En general es requerido por su actitud que es reconocida y valorada.', 3),
            ('c) Coopera con sus jefes y compañeros. Generalmente se muestra interesado en brindar ayuda en el trabajo de los demás.', 2),
            ('d) Dispuesto a prestar ayuda sólo en algunos casos. Prefiere no trabajar en equipo.', 1),
            ('e) Siempre tiene dificultades para cooperar con sus pares y superiores.', 0)
         ]}
    ],

    # ─────────────────────────────────────────────────────────
    # 📋 FORMULARIO 6 
    # ─────────────────────────────────────────────────────────
    6: [
        {'descripcion': 'Volumen de producción de acuerdo con los requerimientos del puesto en el tiempo acordado.',
         'factor': '1.1. CANTIDAD DE TRABAJO',
         'opciones': [
            ('a) Rendimiento excepcionalmente alto. Sobrepasa los márgenes requeridos normalmente en su puesto.', 4),
            ('b) Siempre alcanza y frecuentemente supera el rendimiento requerido en los plazos previstos.', 3),
            ('c) Alcanza los niveles normales de trabajo a un ritmo aceptable y en los plazos establecidos.', 2),
            ('d) Su rendimiento está por debajo de los niveles requeridos para el puesto, o no respeta los plazos establecidos.', 1),
            ('e) Su rendimiento está muy por debajo de los requerimientos y no respeta los plazos establecidos.', 0)
         ]},
        {'descripcion': 'Nivel de terminación y perfección del trabajo que realiza.',
         'factor': '1.2. CALIDAD DE TRABAJO',
         'opciones': [
            ('a) Excepcional nivel de calidad de su trabajo.', 4),
            ('b) Muy buen nivel de calidad de su trabajo.', 3),
            ('c) Adecuado nivel de calidad de su trabajo.', 2),
            ('d) Tiene dificultades para realizar su trabajo con la calidad requerida. Necesita supervisión mayor que la normal.', 1),
            ('e) Falta de calidad en la realización de su trabajo. Necesita constante supervisión.', 0)
         ]},
        {'descripcion': 'Eficiente utilización del tiempo, materiales, procedimientos y métodos de trabajo.',
         'factor': '1.3. MANEJO DE RECURSOS',
         'opciones': [
            ('a) Excelente utilización de los recursos asignados a su puesto. Muy habilidoso para encontrar mejores métodos de trabajo y reducir costos.', 4),
            ('b) Muy efectivo para administrar recursos y reducir costos, mejorar métodos, procedimientos y técnicas.', 3),
            ('c) Buen sentido de la administración de los recursos. Uso adecuado de los métodos y técnicas.', 2),
            ('d) Tiene dificultades para administrar apropiadamente los recursos asignados a su puesto.', 1),
            ('e) No aprovecha los recursos asignados a su puesto, necesita constante monitoreo para administrar su tiempo y procedimientos de trabajo.', 0)
         ]},
        {'descripcion': 'Nivel de conocimientos requeridos para desempeñar las tareas relacionadas con el puesto.',
         'factor': '2. CONOCIMIENTO DE LAS TAREAS',
         'opciones': [
            ('a) Excepcional dominio de todas las fases de su trabajo y tareas relacionadas con el mismo.', 4),
            ('b) Buen dominio de las fases de su trabajo y sólidos conocimientos de sus tareas.', 3),
            ('c) Conoce adecuadamente su trabajo y las tareas relacionadas.', 2),
            ('d) Posee sólo los conocimientos elementales relacionados con su tarea.', 1),
            ('e) Conocimientos insuficientes para el desempleo de las tareas a su cargo.', 0)
         ]},
        {'descripcion': 'Capacidad para comprender y actuar de acuerdo a las pautas establecidas.',
         'factor': '3. CRITERIO',
         'opciones': [
            ('a) Excepcional capacidad para comprender las pautas de trabajo y actuar en consecuencia.', 4),
            ('b) Muy buena capacidad de comprensión de las pautas de trabajo, que le permite actuar minimizando los errores.', 3),
            ('c) Interpreta sin dificultad las pautas de trabajo y responde adecuadamente.', 2),
            ('d) Tiene dificultad para interpretar las pautas de trabajo y necesita frecuentes indicaciones.', 1),
            ('e) Le cuesta comprender las pautas de trabajo y requiere una permanente indicación y monitoreo de sus trabajos.', 0)
         ]},
        {'descripcion': 'Disposición a cooperar con el superior y los demás empleados en la realización de tareas comunes.',
         'factor': '4. COLABORACIÓN',
         'opciones': [
            ('a) Excelente disposición a cooperar ante cada circunstancia o problema que se presente.', 4),
            ('b) Muy dispuesto a cooperar. En general es requerido por su actitud que es reconocida y valorada.', 3),
            ('c) Coopera con sus jefes y compañeros. Generalmente se muestra interesado en brindar ayuda en el trabajo de los demás.', 2),
            ('d) Dispuesto a prestar ayuda sólo en algunos casos. Prefiere no trabajar en equipo.', 1),
            ('e) Siempre tiene dificultades para cooperar con sus pares y superiores.', 0)
         ]}
    ]
}


clasificaciones = {
    1: [("DESTACADO", 56, 37), ("BUENO", 36, 23), ("REGULAR", 22, 9), ("DEFICIENTE", 8, 0)],
    2: [("DESTACADO", 48, 32), ("BUENO", 31, 20), ("REGULAR", 19, 8), ("DEFICIENTE", 7, 0)],
    3: [("DESTACADO", 48, 32), ("BUENO", 31, 20), ("REGULAR", 19, 8), ("DEFICIENTE", 7, 0)],
    4: [("DESTACADO", 40, 27), ("BUENO", 26, 17), ("REGULAR", 16, 7), ("DEFICIENTE", 6, 0)],
    5: [("DESTACADO", 32, 21), ("BUENO", 20, 13), ("REGULAR", 12, 5), ("DEFICIENTE", 4, 0)],
    6: [("DESTACADO", 24, 16), ("BUENO", 15, 10), ("REGULAR", 9, 4), ("DEFICIENTE", 3, 0)],
}





# Título principal
st.title("Formulario de Evaluación de Desempeño")


# Inicializar valor por defecto para evitar errores
previsualizar = False

# Selector de formulario
tipo = st.selectbox(
    "Seleccione el tipo de formulario",
    options=[""] + list(formularios.keys()),
    format_func=lambda x: f"Formulario {x}" if x else "Seleccione una opción",
    key="select_tipo"
)

# Mostrar factores solo si se seleccionó un tipo válido
# Mostrar factores solo si se seleccionó un tipo válido
if tipo != "":
    # Inicializar variables de estado
    if 'previsualizado' not in st.session_state:
        st.session_state.previsualizado = False
    if 'confirmado' not in st.session_state:
        st.session_state.confirmado = False

    # Obtener lista de agentes
    agentes_ref = db.collection("agentes").where("evaluado_2025", "==", False).stream()
    agentes = [{**doc.to_dict(), "id": doc.id} for doc in agentes_ref]
    agentes_ordenados = sorted(agentes, key=lambda x: x["apellido_nombre"])

    if not agentes_ordenados:
        st.warning("⚠️ No hay agentes disponibles para evaluar en 2025.")
        st.stop()  # ❗ DETIENE TODO ANTES DEL FORMULARIO

    # Si hay agentes, mostrar el formulario
    with st.form("form_eval"):
        opciones_agentes = [a["apellido_nombre"] for a in agentes_ordenados]
        seleccionado = st.selectbox("Nombre del evaluado", opciones_agentes)

        agente = next((a for a in agentes_ordenados if a["apellido_nombre"] == seleccionado), None)
        if agente is None:
            st.error("❌ No se encontró el agente seleccionado.")
            st.stop()

        cuil = agente["cuil"]
        apellido_nombre = agente["apellido_nombre"]

        puntajes = []
        respuestas_completas = True

        for i, bloque in enumerate(formularios[tipo]):
            st.subheader(bloque['factor'])
            st.write(bloque['descripcion'])

            opciones = [texto for texto, _ in bloque['opciones']]
            seleccion = st.radio(
                label="Seleccione una opción",
                options=opciones,
                key=f"factor_{i}",
                index=None
            )

            if seleccion is not None:
                puntaje = dict(bloque['opciones'])[seleccion]
                puntajes.append(puntaje)
            else:
                respuestas_completas = False

        # 👇 Este botón DEBE estar dentro del formulario
        previsualizar = st.form_submit_button("🔍 Previsualizar calificación")

   
    # Lógica de previsualización fuera del form
    if previsualizar:
        if respuestas_completas:
            st.session_state.previsualizado = True
            st.session_state.puntajes = puntajes
            st.session_state.respuestas_completas = True
        else:
            st.error("❌ Complete todas las respuestas para previsualizar la calificación")
            st.session_state.previsualizado = False
    
    # Mostrar previsualización si corresponde
    if st.session_state.previsualizado and st.session_state.respuestas_completas:
        total = sum(st.session_state.puntajes)
        rango = clasificaciones.get(tipo, [])
        clasificacion = next(
            (nombre for nombre, maxv, minv in rango if minv <= total <= maxv),
            "Sin clasificación"
        )
        
        st.markdown("---")
        st.markdown(f"### 📊 Puntaje preliminar: {total}")
        st.markdown(f"### 📌 Calificación estimada: **{clasificacion}**")
        st.markdown("---")
        
        # Botones de confirmación
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sí, enviar evaluación"):
                

            
                st.session_state.confirmado = True
                total = sum(st.session_state.puntajes)
                anio = 2025
                tipo_formulario = tipo
                clasificacion = next(
                    (nombre for nombre, maxv, minv in clasificaciones[tipo_formulario] if minv <= total <= maxv),
                    "Sin clasificación"
                )
                
                evaluacion_data = {
                    "apellido_nombre": apellido_nombre,
                    "cuil": cuil,
                    "anio": anio,
                    "formulario": tipo_formulario,
                    "puntaje_total": total,
                    "evaluacion": clasificacion,
                    "_timestamp": firestore.SERVER_TIMESTAMP,
                }
                
                doc_id = f"{cuil}-{anio}"
                db.collection("evaluaciones").document(doc_id).set(evaluacion_data)
                db.collection("agentes").document(cuil).update({"evaluado_2025": True})
            
                st.success(f"📤 Evaluación de {apellido_nombre} enviada correctamente")
                st.balloons()
            
                # Resetear estados
                st.session_state.previsualizado = False
                st.session_state.confirmado = False

                # Resetear todo y recargar
                st.session_state.clear()
                st.rerun()



                
                # También podrías limpiar los campos del formulario aquí
        
        with col2:
            if st.button("❌ No, revisar opciones"):
                st.session_state.previsualizado = False
                st.warning("🔄 Por favor revise las opciones seleccionadas")
    
    # Resetear el estado si se cambia el tipo de formulario
    if 'last_tipo' in st.session_state and st.session_state.last_tipo != tipo:
        st.session_state.previsualizado = False
        st.session_state.confirmado = False
    st.session_state.last_tipo = tipo


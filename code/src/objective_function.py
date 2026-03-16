import networkx as nx
import pyomo.environ as pyo
from pyomo.repn.standard_repn import generate_standard_repn
from pyomo.core.expr.visitor import identify_components
from pyomo.core.base.var import Var
from pyomo.core.base.param import Param

from typing import Any

class PyomoObjectiveBuilder:

    def __init__(self, G: nx.Graph, weight_attr="weight", beta=100.0, gamma=100.0):
        self._m = None 

        self.G = G 
        self.weight_attr = weight_attr
        self.nodes = list(G.nodes())
        self.N = len(self.nodes)
        self.beta = beta
        self.gamma = gamma 

        self._build_objective_function()

    def _build_objective_function(self) -> None:
        m = pyo.ConcreteModel()

        # Sets
        m.I = pyo.Set(initialize=self.nodes, ordered=True)          # vertices
        m.K = pyo.RangeSet(1, self.N)                               # steps 1..N

        m.beta = pyo.Param(mutable=True, initialize=self.beta)
        m.gamma = pyo.Param(mutable=True, initialize=self.gamma)

        # Distance parameter d[i,j] from NetworkX
        def d_init(m, i, j):
            if i == j:
                return 0.0
            # assume complete or that (i,j) exists
            return float(self.G[i][j].get(self.weight_attr, 1.0))
        m.d = pyo.Param(m.I, m.I, initialize=d_init, within=pyo.Reals, mutable=False)

        # Decision variables: x[i,k] = 1 if vertex i is visited at step k
        m.x = pyo.Var(m.I, m.K, domain=pyo.Binary)

        # Constraint for one city per position
        def P_city(m):            
            penalty = 0
            
            for i in m.I:
                s_k = sum(m.x[i,k] for k in m.K)
                e_k = s_k - 1
                penalty +=  e_k * e_k 
            
            return penalty
        
        # Constraint for each city once
        def P_step(m):
            penalty = 0
            
            for k in m.K:
                s_k = sum(m.x[i,k] for i in m.I)
                e_k = s_k - 1
                penalty +=  e_k * e_k 
            
            return penalty
        
        # Helper: next step (wrap-around)
        def k_next(k):
            return 1 if k == self.N else k + 1

        # Bilinear objective (quadratic): sum_k sum_i sum_j d[i,j] * x[i,k] * x[j,k+1]
        def obj_rule(m):
            objfunc = sum(
                m.d[i, j] * m.x[i, k] * m.x[j, k_next(k)]
                for k in m.K
                for i in m.I
                for j in m.I
            ) 
            
            objfunc += m.beta * P_step(m)
            objfunc += m.gamma * P_city(m)
        
            return objfunc

        m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        self._m = m
       
    @property
    def function(self):
        return self._m

class ObjectiveFunctionExtractor:

    def __init__(self, obj) -> None:
        self.repn = generate_standard_repn(obj.expr, quadratic=True)

        self._vars_ordered_unique = None
        self._var_to_id = None
        self._id_to_var = None

        self._linear_terms_cache = self._linear_terms()
        self._quadratic_terms_cache= self._quadratic_terms()

        self._var_ordered_unique()

    def _coef(self, expr):
        # if any(True for _ in identify_components(expr, ctype={Var})):
        if any(isinstance(c, Var) for c in identify_components(expr, component_types={Var})):
            raise ValueError(f"Coeficiente dependente: {expr}")
        
        # if any(True for _ in identify_components(expr, ctype={Param})):
        if any(isinstance(c, Var) for c in identify_components(expr, component_types={Param})):
            return expr
        
        val = pyo.value(expr, exception=False)
        if val is None:
            return expr 
        
        return float(val)
    
    def _var_ordered_unique(self) -> None:
        vars_ordered_unique = []    
        seen_vars = set()
        if self.repn.linear_vars is not None:
            for v in self.repn.linear_vars:
                if v.index() not in seen_vars:
                    vars_ordered_unique.append(v.index())
                    seen_vars.add(v.index())

        if self.repn.quadratic_vars is not None:
            for (v1, v2) in self.repn.quadratic_vars:
                if v1.index() not in seen_vars:
                    vars_ordered_unique.append(v1.index())
                    seen_vars.add(v1.index())
                if v2.index() not in seen_vars:
                    vars_ordered_unique.append(v2.index())
                    seen_vars.add(v2.index())

        var_to_id = {}
        id_to_var = {}
        for pos, var in enumerate(vars_ordered_unique):
            var_to_id[var] = pos
            id_to_var[pos] = var
    
        self._vars_ordered_unique = vars_ordered_unique
        self._var_to_id = var_to_id
        self._id_to_var = id_to_var
    
    @property
    def constant(self) -> Any: 
        # if any(True for _ in identify_components_of_type(self.repn.constant, ctype=Param)):
        if any(isinstance(c, Var) for c in identify_components(self.repn.constant, component_types={Var})):
            return self.repn.constant
        
        value = pyo.value(self.repn.constant, exception=False)
        if value is not None:
            return value
        
        return self.repn.constant
    
    @property
    def vars_ordered_unique(self):
        if self._vars_ordered_unique is not None:
            return self._vars_ordered_unique
        
        raise RuntimeError("Ordem de variáveis inexistente")
    
    @property
    def var_to_id(self):
        if  self._var_to_id is not None:
            return self._var_to_id
        
        raise RuntimeError("Indices de ordem de variáveis inexistente")
    
    @property
    def id_to_var(self):
        if  self._id_to_var is not None:
            return self._id_to_var
        
        raise RuntimeError("Indices de rdem de variáveis inexistente")
        
    def _quadratic_terms(self) -> dict:
        quad = {}
        if self.repn.quadratic_vars is not None:
            for (v1, v2), c in zip(self.repn.quadratic_vars, self.repn.quadratic_coefs):
                if not (v1.index(), v2.index()) in quad:
                    quad[(v1.index(), v2.index())] = self._coef(c)
                else:
                    quad[(v1.index(), v2.index())] += self._coef(c)

        return quad
    
    @property
    def quadratic_terms(self):
        return self._quadratic_terms_cache
        
    def _linear_terms(self) -> dict:
        lin = {}
        if self.repn.linear_vars is not None:
            for v, c in zip(self.repn.linear_vars, self.repn.linear_coefs):
                if not v.index() in lin:
                    lin[v.index()] = self._coef(c)
                else:
                    lin[v.index()] += self._coef(c)

        return lin

    @property
    def linear_terms(self):
        return self._linear_terms_cache
    
    @property
    def has_nonlinear(self): 
        if self.repn.nonlinear_expr is not None:
            return True  

        return False
    
    @property
    def nonlinear(self):
        if self.repn.nonlinear_expr is not None:
            return self.repn.nonlinear_expr
        
        return None
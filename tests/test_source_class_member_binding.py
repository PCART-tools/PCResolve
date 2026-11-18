from pcresolve.flow import FlowAnalyzer


def test_source_class_member_binding_reports_stability_and_hash(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("class Proxy:\n    enabled = bool\n"
                      "    def __init__(self):\n        pass\n", encoding="utf-8")
    analyzer = FlowAnalyzer(project_root=tmp_path)

    fact = analyzer.source_class_member_binding("sample", "Proxy", "__init__", str(source))

    assert fact["schema_version"] == "source-class-member-binding-0.1"
    assert fact["status"] == "stable"
    assert fact["class"]["qualname"] == "Proxy"
    assert fact["member_span"]["lineno"] == 3
    assert fact["member_kind"] == "definition"
    assignment = analyzer.source_class_member_binding(
        "sample", "Proxy", "enabled", str(source)
    )
    assert assignment["member_kind"] == "assignment"
    assert assignment["member_expression"] == "bool"
    assert fact["source_hashes"][str(source)]


def test_source_class_member_binding_detects_module_rebinding(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("class Proxy:\n    def __init__(self):\n        pass\n"
                      "Proxy.__init__ = replacement\n", encoding="utf-8")
    analyzer = FlowAnalyzer(project_root=tmp_path)

    fact = analyzer.source_class_member_binding("sample", "Proxy", "__init__", str(source))

    assert fact["status"] == "may_be_rebound"


def test_source_method_exception_fallback_emits_source_bound_fact(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        try:\n"
        "            instance.resolve()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            return self.fallback(instance)\n", encoding="utf-8")
    fact = FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    )
    assert fact["status"] == "source_bound"
    assert fact["exception"] == "RuntimeError"
    assert fact["receiver_parameter"] == "instance"
    assert fact["lookup_member"] == "resolve"
    assert fact["protected_span"]["lineno"] == 4
    assert fact["source_hashes"][str(source)]


def test_source_method_exception_fallback_rejects_other_return_value(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        try:\n"
        "            instance.resolve()\n"
        "        except RuntimeError:\n"
        "            return True\n", encoding="utf-8")
    assert FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    ) is None


def test_source_method_exception_fallback_rejects_early_return(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        return True\n"
        "        try:\n"
        "            instance.resolve()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            return self.fallback(instance)\n", encoding="utf-8")
    assert FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    ) is None


def test_source_method_exception_fallback_proves_bound_fallback_method(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        if instance is None:\n"
        "            return self\n"
        "        try:\n"
        "            instance.resolve()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            fallback = self.fallback.__get__(instance, owner)\n"
        "            if self.is_attr:\n"
        "                return fallback()\n"
        "            return fallback\n", encoding="utf-8")
    fact = FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    )
    assert fact["fallback_mode"] == "bound_method"


def test_source_method_exception_fallback_accepts_nested_class_value_guard(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        if instance is None:\n"
        "            if self.class_value is not None:\n"
        "                return self.class_value\n"
        "            return self\n"
        "        try:\n"
        "            obj = instance.resolve()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            fallback = self.fallback.__get__(instance, owner)\n"
        "            if self.is_attr:\n"
        "                return fallback()\n"
        "            return fallback\n"
        "        return obj\n", encoding="utf-8")

    fact = FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    )

    assert fact["status"] == "source_bound"
    assert fact["fallback_mode"] == "bound_method"
    assert fact["source_span"]["lineno"] == 14


def test_source_method_exception_fallback_rejects_fallthrough_class_lookup(tmp_path):
    source = tmp_path / "proxy.py"
    source.write_text("class Lookup:\n"
        "    def __get__(self, instance, owner=None):\n"
        "        if instance is None:\n"
        "            if self.class_value is not None:\n"
        "                return self.class_value\n"
        "        try:\n"
        "            instance.resolve()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            return self.fallback(instance)\n", encoding="utf-8")

    assert FlowAnalyzer(project_root=tmp_path).source_method_exception_fallback(
        "proxy", "Lookup", "__get__", str(source)
    ) is None

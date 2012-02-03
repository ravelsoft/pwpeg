from . import helpers, pwpeg

class AstNode(object):
    def __repr__(self):
        return "<{0}>".format(self.__class__.__name__)

    def to_python(self, ctx=dict(), indent=0):
        return "-"


class AstPredicate(AstNode):
    def __init__(self, code):
        self.code = code


    def __repr__(self):
        return "{{{0}}}".format(self.code)

    def to_python(self, ctx=dict(), indent=0):
        return "lambda {0}: {1}".format(", ".join(ctx["args"]), self.code)


class AstRuleSingle(AstNode):
    def __init__(self, rule, repetition=None):
        self.label = None
        self.rule = rule
        self.repetition = None
        self.matching = None

    def set_label(self, label):
        self.label = label
        return self

    def set_repetition(self, repetition):
        self.repetition = repetition
        return self

    def set_matching(self, matching):
        self.matching = matching
        return self

    def __repr__(self):
        label = ""
        repetition = self.repetition or ""
        if self.label:
            label = self.label + ":"
        return "{0}{1}{2}".format(label, self.rule, repetition)

    def to_python(self, ctx=dict(), indent=0):
        # FIXME the repetitions !
        res = None

        if isinstance(self.rule, AstNode):
            res = self.rule.to_python(ctx, indent)
        else:
            res = self.rule

        rep = self.repetition
        if rep:
            if rep[0] == rep[1]:
                res = "Exactly({0}, {1})".format(rep[0], res)
            elif rep[0] == 0 and rep[1] == 1:
                res = "Optional({0})".format(res)
            elif (rep[0] == 0 or rep[0] == -1) and rep[1] == -1:
                res = "ZeroOrMore({0})".format(res)
            elif rep[0] == 1 and rep[1] == -1:
                res = "OneOrMore({0})".format(res)
            else:
                res = "Repetition({0}, {1}, {2})".format(rep[0], rep[1], res)

        if self.matching == "!":
            res = "Not({0})".format(res)
        elif self.matching == "&":
            res = "And({0})".format(res)
        else:
            res = res

        return res


class AstRuleCall(AstRuleSingle):
    def to_python(self, ctx, indent):
        rulename = self.rule

        paren_start = self.rule.find("(")

        if paren_start != -1:
            rulename = self.rule[:paren_start]

        if not rulename in ctx["seen_rules"]:
            ctx["asked_rules"].add(rulename)

        return super(AstRuleCall, self).to_python(ctx, indent)


class AstCode(AstNode):
    def __init__(self, code):
        self.code = code

    def __repr__(self, ctx=dict(), indent=0):
        code = ""
        if self.code:
            code = self.code[:10]
            if len(self.code) > 10:
                code += "..."
        return code



class AstRuleGroup(AstNode):
    def __init__(self, rules, action=None):
        self.rules = rules
        self.action = action

    def set_action(self, action):
        self.action = action
        return self

    def __repr__(self):
        rules = " ".join([repr(r) for r in self.rules])

        action = ""

        if self.action:
            action = " ({0})".format(repr(self.action))

        return "{0}{1}".format(rules, action)

    def to_python(self, ctx=dict(), indent=0):
        ctx = dict(**ctx)
        ctx["args"] = []

        res = []

        i = 0
        for r in self.rules:

            if not getattr(r, "matching", None) and not isinstance(r, AstPredicate):
                ctx["args"].append(getattr(r, "label", None) or "_{0}".format(i))
                i += 1

            res.append(r.to_python(ctx, indent))

        if self.action:
            if self.action.find('\n') is -1 and self.action.find('return') is -1:
                res.append("Action(lambda {0}:{1})".format(", ".join(ctx["args"]), self.action))
            else:
                action_name = "action_{0}".format(ctx["last_action"][0])
                res.append("Action({0})".format(action_name))
                ctx["last_action"][0] += 1

                action_body = []

                action_body.append("def {0}({1}):".format(action_name, ", ".join(ctx["args"])))
                for l in self.action.split("\n"):
                    action_body.append("    " + l)
                action_body.append("")

                ctx["actions"].append("\n".join(action_body))

        if len(res) > 1:
            return "(" + ", ".join(res) + ")"
        return res[0]



class AstRuleEither(AstRuleGroup):
    def __repr__(self):
        rep = " | ".join([repr(r) for r in self.rules])
        if len(self.rules) > 1:
            return "[" + rep + "]"
        return rep

    def to_python(self, ctx=dict(), indent=0):
        if len(self.rules) == 1:
            return self.rules[0].to_python(ctx, indent)

        normal_ind = " " * indent
        ind = " " * (indent + 4)

        return "Either(\n{0}{1}\n{2})".format(ind,
            ",\n{0}".format(ind).join([r.to_python(ctx, indent + 4) for r in self.rules]),
            normal_ind)


class AstRuleDecl(AstNode):
    def __init__(self, name):
        self.name = name
        self.args = None
        self.productions = None
        self.skip = None

    def set_productions(self, productions):
        self.productions = productions
        return self

    def set_args(self, args):
        self.args = args
        return self

    def set_skip(self, skip):
        self.skip = skip
        return self

    def __repr__(self):
        return "<{0}{1}>".format(self.name, self.args)


class AstFile(AstNode):

    def __init__(self, code, rules, endcode):
        self.code = code or ""
        self.rules = rules
        self.endcode = endcode or ""

    def __repr__(self):
        return "{0}{1}{2}".format(self.code, self.rules, self.endcode)
